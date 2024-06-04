from flask import *
from flask import Flask, request, render_template, session, url_for, redirect 
from datetime import date
import matplotlib.pyplot as plt 
import os, json, io, requests
import matplotlib, base64
import numpy as np 
import mysql.connector
import hashlib, re
matplotlib.use('Agg')

try:
  mydb = mysql.connector.connect(
  host="localhost",
  user="nations",
  password="nations!",
  database="nations"
)
except: 
    print("Error Connecting to Database!")

mycursor = mydb.cursor()

app = Flask(__name__)

app.secret_key = '?HolyCow!'

def get_user_id_and_username():
    id = session.get('id')
    username = session.get('username')
    return id, username

def get_today():
    return date.today()

def get_existing_record(id, today):
    mycursor.execute('SELECT * FROM Cfood WHERE id = %s AND date = %s', (id, today,))
    return mycursor.fetchone()

def get_existing_nutrition(id, today):
    mycursor.execute('SELECT cal, calG, protein, proteinG, carbs, carbsG, fats, fatsG FROM Cfood WHERE id = %s AND date = %s', (id, today,))
    return mycursor.fetchone()

def get_existing_workout(id, today, name):
    mycursor.execute('SELECT name, date, time, weight, sets, reps FROM Cworkouts WHERE id = %s AND date = %s AND name = %s', (id, today, name))
    return mycursor.fetchone()

def get_existing_workouts(id, today):
    mycursor.execute('SELECT name, time, weight, sets, reps FROM Cworkouts WHERE id = %s AND date = %s', (id, today))
    return mycursor.fetchall()

def get_existing_goals(id):
    mycursor.execute('SELECT goal, typeG FROM Cgoals WHERE id = %s', (id,))
    return mycursor.fetchall()

def get_existing_goal(id,goal):
    mycursor.execute('SELECT goal, typeG FROM Cgoals WHERE id = %s AND goal = %s', (id,goal))
    return mycursor.fetchone()

def update_or_insert_record(id, username, today, data):
    cal, calG, protein, proteinG, carbs, carbsG, fats, fatsG = data[:8]
    existing_record = get_existing_record(id, today)

    if existing_record:
        mycursor.execute('UPDATE Cfood SET cal = %s, calG = %s, protein = %s, proteinG = %s, '
                         'carbs = %s, carbsG = %s, fats = %s, fatsG = %s '
                         'WHERE id = %s AND date = %s',
                         (cal, calG, protein, proteinG, carbs, carbsG, fats, fatsG, id, today))
    else:
        mycursor.execute('INSERT INTO Cfood VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)',
                         (id, username, today, cal, calG, protein, proteinG, carbs, carbsG, fats, fatsG))

    mydb.commit()
    
def update_or_insert_goals(id, username, today, data):
    goal = data[0]
    typeG = data[1]
    existing_record = get_existing_goal(id,goal)

    if existing_record:
        mycursor.execute('UPDATE Cgoals SET goal = %s, typeG = %s '
                         'WHERE id = %s AND date = %s AND goal = %s',
                         (goal, typeG, id, today, goal))
    else:
        mycursor.execute('INSERT INTO Cgoals VALUES (%s, %s, %s, %s, %s)',
                         (id, username, today, goal, typeG))

    mydb.commit()

def update_or_insert_workout(id, username, today, data):
    exerciseName, timeSpent, weightUsed, numSets, numReps = data[:5]
    existing_record = get_existing_workout(id, today, exerciseName)

    if existing_record:
        mycursor.execute('UPDATE Cworkouts SET name = %s, time = %s, weight = %s, sets = %s, '
                         'reps = %s'
                         'WHERE id = %s AND date = %s AND name = %s',
                         (exerciseName, timeSpent, weightUsed, numSets, numReps, id, today, exerciseName))
    else:
        mycursor.execute('INSERT INTO Cworkouts VALUES (%s, %s, %s, %s, %s, %s, %s, %s)',
                         (id, username, today, exerciseName, timeSpent, weightUsed, numSets, numReps))

    mydb.commit()
    
def del_workout(data, id):
    exerciseName = data[0]
    mycursor.execute('DELETE from Cworkouts WHERE name = %s AND id = %s', (exerciseName,id))
    mydb.commit()
    
def del_goal(data, id):
    goal = data[0]
    mycursor.execute('DELETE from Cgoals WHERE goal = %s AND id = %s', (goal,id))
    mydb.commit()

@app.route('/Login/', methods=['GET', 'POST'])
def login():

    msg = ''
    if request.method == 'POST' and 'username' in request.form and 'password' in request.form:

        username = request.form['username']
        password = request.form['password']
        hash = password + app.secret_key
        hash = hashlib.sha1(hash.encode())
        password = hash.hexdigest()

        mycursor.execute('SELECT * FROM Caccounts WHERE username = %s AND password = %s', (username, password,))
        
        account = mycursor.fetchone()
        
        if account:
            session['username'] = account[1]
            session['id'] = account[0]
            session['loggedin'] = True
            return redirect(url_for('home'))
        else:
            msg = 'Incorrect username/password!'

    return render_template('Login.html', msg=msg)

@app.route('/Login/register', methods=['GET', 'POST'])
def register():
    
    msg = ''
    if request.method == 'POST' and 'username' in request.form and 'password' in request.form:
        username = request.form['username']
        password = request.form['password']
        
        mycursor.execute('SELECT * FROM Caccounts WHERE username = %s', (username,))
        account = mycursor.fetchone()
        if account:
            msg = 'Account already exists!'
        elif not re.match(r'[A-Za-z0-9]+', username):
            msg = 'Username must contain only characters and numbers!'
        elif not username or not password:
            msg = 'Please fill out the form!'
        else:
            hash = password + app.secret_key
            hash = hashlib.sha1(hash.encode())
            password = hash.hexdigest()
            mycursor.execute('INSERT INTO Caccounts VALUES (NULL, %s, %s)', (username, password,))
            mydb.commit()
            msg = 'You have successfully registered!'

    elif request.method == 'POST':
        msg = 'Please fill out the form!'
        
    return render_template('Register.html', msg=msg)

@app.route('/logout')
def logout():
   session.pop('loggedin', None)
   session.pop('username', None)
   return redirect(url_for('login'))

@app.route('/History', methods=['GET', 'POST'])
def history(): 
    if 'loggedin' not in session:
        return redirect(url_for('login'))

    try:
        id, username = get_user_id_and_username()
        if request.method == 'POST':
            data = request.get_json()
            dateS = data
            nutrition = get_existing_nutrition(id, dateS)
            workout = get_existing_workouts(id, dateS)
            if nutrition:
                nutrition_data = {
                    'protein': nutrition[2],
                    'carbs': nutrition[4],
                    'fats': nutrition[6]
                } 
            else: 
                nutrition_data = {
                    'protein': 1,
                    'carbs': 1,
                    'fats': 1
                }
                
            labels = list(nutrition_data.keys())
            values = list(nutrition_data.values())

            plt.figure(figsize=(4, 2))
            plt.pie(values, labels=labels, autopct='%1.1f%%', startangle=140)
            plt.axis('equal') 
            plt.title('Nutrition Distribution on ' + dateS)

            bytes_image = io.BytesIO()
            plt.savefig(bytes_image, format='png')
            bytes_image.seek(0)

            image = base64.b64encode(bytes_image.read()).decode('utf-8')
            plt.close()
            return jsonify({
                'nutrition': nutrition,
                'workout': workout,
                'image': image,
            })

        else:
            return render_template('History.html')
    
    except mysql.connector.Error as err:
        print("MySQL Error:", err)
        return "An error occurred while processing your request."
    
    except Exception as e:
        print("Error:", e)
        return "An unexpected error occurred while processing your request."

@app.route('/Home', methods=['GET', 'POST'])
def home(): 
    if 'loggedin' in session:
        id = session['id']
        user = session['username']
        today = date.today()
        
        try:
            mycursor.execute('SELECT * FROM Cfood WHERE id = %s AND  date = %s', (id, today,))
            record = mycursor.fetchone()

            if record:
                nutrition_data = {
                    'protein': record[5],
                    'carbs': record[7],
                    'fats': record[9]
                }
            else: 
                nutrition_data = {
                    'protein': 1,
                    'carbs': 1,
                    'fats': 1
                }

            labels = list(nutrition_data.keys())
            values = list(nutrition_data.values())

            plt.figure(figsize=(6, 4))
            plt.pie(values, labels=labels, autopct='%1.1f%%', startangle=140)
            plt.axis('equal') 
            plt.title('Nutrition Distribution')

            bytes_image = io.BytesIO()
            plt.savefig(bytes_image, format='png')
            bytes_image.seek(0)

            base64_image = base64.b64encode(bytes_image.read()).decode('utf-8')
            plt.close()

            if record:
                calories = {
                    'calorie goal': record[4],
                    'calories eaten': record[3],
                }
            else: 
                calories = {
                    'calorie goal': 1,
                    'calories eaten': 1,
                }

            labels = list(calories.keys())
            values = list(calories.values())

            plt.figure(figsize=(6, 4))
            plt.pie(values, labels=labels, autopct='%1.1f%%', startangle=140)
            plt.axis('equal') 
            plt.title('Caloric Goal')

            bytes_image = io.BytesIO()
            plt.savefig(bytes_image, format='png')
            bytes_image.seek(0)

            img2 = base64.b64encode(bytes_image.read()).decode('utf-8')
            plt.close()

            workout = get_existing_workouts(id, today)

            if workout:
                workout = json.dumps(workout)

            return render_template('Home.html', record=record, user=user, workout=workout, pie_chart1=base64_image, pie_chart2=img2)
        
        except mysql.connector.Error as err:
            # Handle MySQL errors
            print(f"MySQL error: {err}")
            # Redirect user to an error page or render a specific error template
            return render_template('error.html', error_message="Database error occurred. Please try again later.")
        
        except Exception as e:
            # Handle other exceptions
            print(f"Error: {e}")
            # Redirect user to an error page or render a specific error template
            return render_template('error.html', error_message="An unexpected error occurred. Please try again later.")
    
    # If 'loggedin' is not in session, redirect to login page
    return redirect(url_for('login'))

@app.route('/Food', methods=['GET', 'POST'])
def food():
    if 'loggedin' not in session:
        return redirect(url_for('login'))

    try:
        id, username = get_user_id_and_username()
        today = get_today()

        if request.method == 'POST':
            data = request.get_json()
            update_or_insert_record(id, username, today, data)
            return render_template('Food.html')
        else:
            record = get_existing_nutrition(id, today)
            record_json = json.dumps(record)
            return render_template('Food.html', record=record_json)

    except mysql.connector.Error as err:
        print("MySQL Error:", err)
        return "An error occurred while processing your request."

    except Exception as e:
        print("Error:", e)
        return "An unexpected error occurred while processing your request."



@app.route('/Goals', methods=['GET', 'POST'])
def goals(): 
    if 'loggedin' not in session:
        return redirect(url_for('login'))

    try:
        id, username = get_user_id_and_username()
        today = get_today()

        if request.method == 'POST':
            data = request.get_json()
            if data[2] == "add":
                update_or_insert_goals(id, username, today, data)
                goal = get_existing_goals(id)
                return jsonify({'goal': goal})
            elif data[2] == "delete":
                del_goal(data, id) 
                goal = get_existing_goals(id)
                return jsonify({'goal': goal})
        else:
            goal = get_existing_goals(id)
            goal_json = json.dumps(goal)
            return render_template('Goals.html', goal=goal_json)

    except mysql.connector.Error as err:
        print("MySQL Error:", err)
        return "An error occurred while processing your request."

    except Exception as e:
        print("Error:", e)
        return "An unexpected error occurred while processing your request."


@app.route('/Workout', methods=['GET', 'POST'])
def workout():
    if 'loggedin' not in session:
        return redirect(url_for('login'))

    try:
        id, username = get_user_id_and_username()
        today = get_today()

        if request.method == 'POST':
            data = request.get_json()
            if data[5] == "add":
                update_or_insert_workout(id, username, today, data)
                workout = get_existing_workouts(id, today)
                return jsonify({'workout': workout}) 
            elif data[5] == "delete":
                del_workout(data, id)
                workout = get_existing_workouts(id, today)
                return jsonify({'workout': workout}) 
        else:
            workout = get_existing_workouts(id, today)
            workout_json = json.dumps(workout)
            return render_template("Workout.html", workout=workout_json)

    except mysql.connector.Error as err:
        print("MySQL Error:", err)
        return "An error occurred while processing your request."

    except Exception as e:
        print("Error:", e)
        return "An unexpected error occurred while processing your request."
    
@app.route('/Resources')
def resources():
	return render_template("Resources.html")


if __name__ == '__main__':
   app.run('0.0.0.0', port = 25252, debug = True)