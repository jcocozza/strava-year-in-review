from flask import Flask, render_template, Markup, redirect, request, url_for,session
import sql_functions
import get_user_activity_data
from get_user_activity_data import approval_link
import os

cwd = os.getcwd()

app = Flask(__name__)

@app.route('/login', methods=['GET','POST'])
def login():
    # Output message if something goes wrong...
    msg = ''
    result = None
    # Check if "username" and "password" POST requests exist (user submitted form)
    if request.method == 'POST' and 'username' in request.form and 'password' in request.form:
        # Create variables for easy access
        username = str(request.form['username'])
        password = str(request.form['password'])

        # Check if account exists
        query = """SELECT us.username, us.password FROM users us WHERE us.username = %s AND us.password = %s ;""" % (username, password)
        result = sql_functions.local_sql_to_df(query)

    # If account exists in accounts table in out database
    if result:
        # Create session data, we can access this data in other routes
        session['loggedin'] = True
        session['id'] = result['user_id']
        session['username'] = result['username']
        # Redirect to home page
        return 'Logged in successfully!' #redirect('/', code=302)
    else:
        # Account doesnt exist or username/password incorrect
        msg = 'Incorrect username/password!'

    return render_template('login.html', msg='')

@app.route('/')
def welcome_page():
    return render_template('home.html')

@app.route('/get_data')
def get_approved():
    return redirect(approval_link, code=302)

@app.route('/exchange_token', methods=['GET'])
def parse_request():
    authorization_code = request.args['code'] # grabbing the authorization code that is returned by strava in the URL
    token = get_user_activity_data.get_user_access_token(authorization_code) # getting the access token
    results = get_user_activity_data.get_user_activity_data(token) # returns a dataframe of the data (data is also saved to a csv)

    path = cwd + '/data/data.csv'
    sql_functions.upload_data_file_to_local(path, 'strava_app_activity_data')
    return redirect('/')

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