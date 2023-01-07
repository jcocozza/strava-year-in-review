from flask import Flask, render_template, Markup, redirect, request, url_for,session
import sql_functions
import get_user_activity_data
from get_user_activity_data import approval_link
import pandas as pd
import os

cwd = os.getcwd()
repo_dir = cwd + '/strava-year-in-review'
cwd = repo_dir

app = Flask(__name__)
app.secret_key = 'blahblahblahblahblah'

@app.route('/')
def enter():
    return redirect(url_for('welcome_page'))

@app.route('/login', methods=['GET','POST'])
def login():
    # Output message if something goes wrong...
    msg = ''
    # Check if "username" and "password" POST requests exist (user submitted form)
    if request.method == 'POST' and 'username' in request.form and 'password' in request.form:
        # Create variables for easy access
        username = str(request.form['username'])
        password = str(request.form['password'])

        # Check if account exists
        query = """SELECT * FROM users WHERE username = '%s' AND password = '%s';""" % (username, password)
        result = sql_functions.local_sql_to_df(query)

        # If account exists in user table in out database
        if not result.empty:
            # Create session data, we can access this data in other routes
            session['loggedin'] = True
            session['id'] = int(result['user_id'][0])
            session['username'] = str(result['username'][0])
            # Redirect to home page
            return redirect('/home', code=302)
    else:
        # Account doesnt exist or username/password incorrect
        msg = 'Incorrect username/password!'

    return render_template('login.html', msg=msg)

@app.route('/logout')
def logout():
    # Remove session data, this will log the user out
   session.pop('loggedin', None)
   session.pop('id', None)
   session.pop('username', None)
   # Redirect to login page
   return redirect(url_for('login'))

@app.route('/register', methods=['GET','POST'])
def register():
    # Output message if something goes wrong...
    msg = ''
    # Check if "username", "password" and "email" POST requests exist (user submitted form)
    if request.method == 'POST' and 'username' in request.form and 'password' in request.form:
        # Create variables for easy access
        username = request.form['username']
        password = request.form['password']

        # Check if account exists; if it doesn't insert info into the table
        query = """SELECT * FROM users WHERE username = '%s' AND password = '%s';""" % (username, password)
        result = sql_functions.local_sql_to_df(query)
        # If account exists in user table
        if not result.empty:
            msg = 'Account already exists!'
        elif not username or not password:
            msg = 'Please fill out the form!'
        else:
            data = {
                'username': username,
                'password': password,
                'athlete_id': None,
                'refresh_token': None
                }
            df = pd.DataFrame(data, index=[0])
            sql_functions.df_to_local_sql(df, 'users')
            msg = 'Successfully Registered'

    elif request.method == 'POST':
        # Form is empty... (no POST data)
        msg = 'Please fill out the form!'
    # Show registration form with message (if any)
    return render_template('register.html', msg=msg)


@app.route('/home')
def welcome_page():
    if 'loggedin' in session: # only see home if logged in
        return render_template('home.html')
    return redirect(url_for('login'))

@app.route('/get_data')
def get_approved():
    return redirect(approval_link, code=302)

@app.route('/exchange_token', methods=['GET'])
def parse_request():
    authorization_code = request.args['code'] # grabbing the authorization code that is returned by strava in the URL
    access_token, refresh_token = get_user_activity_data.get_user_access_token(authorization_code) # getting the access token
    results = get_user_activity_data.get_user_activity_data(access_token) # returns a dataframe of the data (data is also saved to a csv)

    sql_functions.insert_refresh_token(refresh_token) # adds refresh token to user data

    path = cwd + '/data/data.csv'
    sql_functions.upload_data_file_to_local(path, 'strava_app_activity_data')
    return redirect('/home')

@app.route('/refresh_data')
def refresh_data():
    sql = "SELECT refresh_token FROM users user_id = %s" % (session['id'],)
    data = sql_functions.local_sql_to_df(sql) # get refresh token from db
    refresh_token = data['refresh_token'][0]
    access_token = get_user_activity_data.returning_user_access_token(refresh_token) # getting access token
    results = get_user_activity_data.get_user_activity_data(access_token) # returns a dataframe of the data (data is also saved to a csv)

    path = cwd + '/data/returing_data.csv'
    sql_functions.upload_data_file_to_local(path, 'strava_app_activity_data')

@app.route('/summary_data')
def summarize():
    query = """SELECT SUM((ad.distance/1609.344)) AS DIST, SUM((ad.moving_time/60)) AS mov_time, SUM((ad.moving_time/60))/SUM((ad.distance/1609.344)) AS average_speed, SUM(ad.total_elevation_gain) AS total_elevation_gain
    FROM strava_app_activity_data ad
    WHERE ad.`type` = "Run" AND YEAR(start_date) = 2022;"""

    data = sql_functions.local_sql_to_df(query)
    return render_template('summary.html', data_table=Markup(data.to_html()))

@app.route('/activity_list')
def activity_list():
    query = """SELECT ad.name, ad.id, (ad.distance/1609.344) AS distance, (ad.moving_time/60) AS moving_time, (1609.344/(ad.average_speed*60)) AS average_speed, ad.start_date_local
    FROM strava_app_activity_data ad
    WHERE ad.`type` = "Run" AND YEAR(start_date) = 2022;"""

    data = sql_functions.local_sql_to_df(query)
    return render_template('activity_list.html', data_table=Markup(data.to_html()))

if __name__ == '__main__':
    app.secret_key = os.urandom(12)
    app.run(host='0.0.0.0',debug=False, port=8888)