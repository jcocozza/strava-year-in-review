########## IMPORTS ##########
#region - imports
from flask import Flask, render_template, Markup, redirect, request, url_for,session
import sql_functions
import get_user_activity_data
from get_user_activity_data import approval_link
import pandas as pd
import os
import threading
from threading import Thread
import weekly_report_functions
import single_activity_analysis
import pendulum
from datetime import datetime
#endregion - imports

########## Setting working directory ##########
cwd = os.getcwd()
repo_dir = cwd + '/strava-year-in-review'
cwd = repo_dir

app = Flask(__name__)
app.secret_key = 'blahblahblahblahblah'

# Base Route; Redirects to to /home for password protection
@app.route('/')
def enter():
    return redirect(url_for('welcome_page'))

# Will welcome user provided they are logged in; otherwise redirect to login
@app.route('/home')
def welcome_page():
    if 'loggedin' in session: # only see home if logged in
        return render_template('home.html', user=session['username'])
    return redirect(url_for('login'))

# Requires username and password to login
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

# Drops user credentials from the session 
# redirects to login page
@app.route('/logout')
def logout():
    # Remove session data, this will log the user out
   session.pop('loggedin', None)
   session.pop('id', None)
   session.pop('username', None)
   # Redirect to login page
   return redirect(url_for('login'))

# adjacent to login; user inputs username, password
# does NOT auto-login; redirects to login page
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
            return redirect(url_for('login'))

    elif request.method == 'POST':
        # Form is empty... (no POST data)
        msg = 'Please fill out the form!'
    # Show registration form with message (if any)
    return render_template('register.html', msg=msg)

# any time loading page is called, it will include a process to run, and a redirect url to go to when the process is completed
# basically renders a little loading simple
@app.route('/loading_page', methods=['GET'])
def loading():
    
    p = request.args['process']
    r = request.args['redirect']
    process_url = url_for(p) 
    redirect_url = url_for(r)   

    return render_template('loading.html', redirect=redirect_url, process=process_url)

########## STRAVA API CONNECTION ##########
#region - Strava

# Page for all strava stuff; currently just a bunch of links
@app.route('/strava')
def strava():
    return render_template('strava_page.html')

#region - Initial Strava Connection
# handling user approval and getting authorization code
@app.route('/strava/get_data')
def get_approved():
    return redirect(approval_link, code=302)

# using authorization code (returned by link in /strava/get_data) to get tokens for users and put them in the database
@app.route('/strava/exchange_token', methods=['GET'])
def parse_request():
    authorization_code = request.args['code'] # grabbing the authorization code that is returned by strava in the URL
    access_token, refresh_token, athlete_data = get_user_activity_data.get_user_access_token(authorization_code) # getting the access token
    results = get_user_activity_data.get_user_activity_data(access_token, session['id']) # returns a dataframe of the data (data is also saved to a csv)

    sql_functions.insert_refresh_token(refresh_token) # adds refresh token to user data
    sql_functions.insert_athlete_id(athlete_data['id']) # adds athlete_id to user data

    path = cwd + '/data/' + str(session['id']) + '_data.csv'
    sql_functions.upload_data_file_to_local(path, 'strava_app_activity_data')

    return redirect('/strava')
#endregion - Initial Strava Connection

#region - Strava Tasks
# For users that exists in the database and have already connected to strava this will refresh their strava data
@app.route('/strava/refresh_data')
def refresh_data():
    refresh_token = sql_functions.get_refresh_token()
    access_token = get_user_activity_data.returning_user_access_token(refresh_token) # getting access token
    results = get_user_activity_data.get_user_activity_data(access_token, session['id']) # returns a dataframe of the data (data is also saved to a csv)

    path = cwd + '/data/' + str(session['id']) + '_data.csv'
    sql_functions.upload_data_file_to_local(path, 'strava_app_activity_data')

    return render_template('strava_page.html') #redirect('/strava')

# Summary of yearly running activities
@app.route('/strava/summary_data')
def summarize():
    athlete_id = sql_functions.get_athlete_id()
    query = """SELECT SUM((ad.distance/1609.344)) AS DIST, SUM((ad.moving_time/60)) AS mov_time, SUM((ad.moving_time/60))/SUM((ad.distance/1609.344)) AS average_speed, SUM(ad.total_elevation_gain) AS total_elevation_gain
    FROM strava_app_activity_data ad
    WHERE ad.`type` = "Run" AND YEAR(start_date) = 2022 AND ad.`athlete.id` = %s;""" % (athlete_id)

    data = sql_functions.local_sql_to_df(query)
    return render_template('summary.html', data_table=Markup(data.to_html()))

# List of Yearly Running Activities
@app.route('/strava/activity_list')
def activity_list():
    athlete_id = sql_functions.get_athlete_id()
    query = """SELECT DISTINCT ad.name, ad.id, (ad.distance/1609.344) AS distance, (ad.moving_time/60) AS moving_time, (1609.344/(ad.average_speed*60)) AS average_speed, ad.start_date_local
    FROM strava_app_activity_data ad
    WHERE ad.`type` = "Run" AND YEAR(start_date) = 2022 AND ad.`athlete.id` = %s;""" % (athlete_id)

    data = sql_functions.local_sql_to_df(query)
    return render_template('activity_list.html', data_table=Markup(data.to_html()))

# Query Activites in a Date Range; Provides some summary statistcs about them
@app.route('/strava/ad_hoc', methods=['GET','POST'])
def ad_hoc():
    user_id = session['id']
    # Output message if something goes wrong
    msg = ''
    # Check if "start_date", "end_date" POST requests exist (user submitted form)
    # date in the form of YYYY-MM-DD
    if request.method == 'POST' and 'start_date' in request.form and 'end_date' in request.form:
        # Create variables for easy access
        start_date = request.form['start_date']
        end_date = request.form['end_date']

        # calc number of days difference
        day1 = datetime.strptime(start_date, "%Y-%m-%d")
        day2 = datetime.strptime(end_date, "%Y-%m-%d")

        delta = day2 - day1

        # Make sure user fills out info
        if not start_date or not end_date:
            msg = 'Please fill out the form!'
        else:
            week_tuple = (start_date, end_date)

            header = f'Summary for {start_date} to {end_date}'

            ########## GETTING DATA ##########
            athlete_id = sql_functions.get_athlete_id()
            week_activity_data = weekly_report_functions.get_week_activity_data(week_tuple, athlete_id)
            week_heartrate_data = weekly_report_functions.get_week_heartrate_data(week_activity_data, session['id'])
            week_lap_data = weekly_report_functions.get_timeinterval_lap_data(week_activity_data, session['id'])

            bin_array = [0, 150, 160, 205]
            labels = single_activity_analysis.zones(bin_array)

            ########## DATA ANALYSIS ##########
            total_mileage = weekly_report_functions.total_distance(week_activity_data)
            avg_mileage = weekly_report_functions.average_distance(week_activity_data, delta.days)
            total_time = weekly_report_functions.total_time(week_activity_data)
            avg_time = weekly_report_functions.average_time(week_activity_data, delta.days)

            activity_table = weekly_report_functions.activity_table(week_activity_data)
            binned_zone_data = weekly_report_functions.zone_data(week_heartrate_data, bin_array, labels)

            ########## PLOTS ##########
            hr_plot = weekly_report_functions.heart_rate_zone_plots(binned_zone_data, user_id)
            mileage = weekly_report_functions.mileage_graph(week_activity_data, user_id)
            time = weekly_report_functions.time_graph(week_activity_data, user_id)

            src1 = url_for('static', filename=f'charts/{user_id}_weekly_hr_pie.html')
            src2 = url_for('static', filename=f'charts/{user_id}_weekly_hr_hist.html')
            src3 = url_for('static', filename=f'charts/{user_id}_weekly_mileage_bar.html')
            src4 = url_for('static', filename=f'charts/{user_id}_weekly_time_bar.html')

            msg = 'Data Query Successful'

            # redirect to data table with rest of page
            return render_template('ad_hoc_results.html', msg=msg, data_table=Markup(activity_table), src1=src1, src2=src2, src3=src3, src4=src4)

    elif request.method == 'POST':
        # Form is empty... (no POST data)
        msg = 'Please fill out the form!'
    # Show page
    return render_template('ad_hoc_results.html', msg=msg)

# Provides a weekly summary of all strava activity for the most recent week
# VERY similar to ad_hoc except for the present week
@app.route('/strava/weekly_summary')
def weekly_summary():
    ########## PARAMETERS ##########
    bin_array = [0, 150, 160, 205]
    labels = single_activity_analysis.zones(bin_array)
    user_id = session['id']
    ####### WEEK INFORMATION #######
    today = pendulum.now()
    beginning = today.start_of('week')
    ending = today.end_of('week')

    week_start = beginning.strftime("%Y-%m-%d")
    week_end = ending.strftime("%Y-%m-%d")

    week_tuple = (week_start, week_end)

    header = f'Summary for {week_start} to {week_end}'

    ########## GETTING DATA ##########
    athlete_id = sql_functions.get_athlete_id()
    week_activity_data = weekly_report_functions.get_week_activity_data(week_tuple, athlete_id)
    week_heartrate_data = weekly_report_functions.get_week_heartrate_data(week_activity_data, session['id'])
    week_lap_data = weekly_report_functions.get_timeinterval_lap_data(week_activity_data, session['id'])

    ########## DATA ANALYSIS ##########
    total_mileage = weekly_report_functions.total_distance(week_activity_data)
    avg_mileage = weekly_report_functions.average_distance(week_activity_data, 7)
    total_time = weekly_report_functions.total_time(week_activity_data)
    avg_time = weekly_report_functions.average_time(week_activity_data, 7)

    activity_table = weekly_report_functions.activity_table(week_activity_data)
    binned_zone_data = weekly_report_functions.zone_data(week_heartrate_data, bin_array, labels)

    ########## PLOTS ##########
    hr_plot = weekly_report_functions.heart_rate_zone_plots(binned_zone_data, user_id)
    mileage = weekly_report_functions.mileage_graph(week_activity_data, user_id)
    time = weekly_report_functions.time_graph(week_activity_data, user_id)

    src1 = url_for('static', filename=f'charts/{user_id}_weekly_hr_pie.html')
    src2 = url_for('static', filename=f'charts/{user_id}_weekly_hr_hist.html')
    src3 = url_for('static', filename=f'charts/{user_id}_weekly_mileage_bar.html')
    src4 = url_for('static', filename=f'charts/{user_id}_weekly_time_bar.html')

    return render_template('weekly_summary.html', header=header, activity_table=Markup(activity_table), src1=src1, src2=src2, src3=src3, src4=src4)

# An analysis of an individual activity; will come with ?activity_id=XXXXXXXX in url for the GET method
@app.route('/strava/weekly_summary/activity_analysis', methods=['GET'])
def activity_analysis():
    ########## PARAMETERS ##########
    user_id = session['id']
    activity_id = request.args['id'] # grabbing the activity_id returned in the URL
    bin_array = [0, 150, 160, 205]
    
    single_activity_analysis.do_activity_analysis(activity_id, user_id, bin_array)

    # urls for plots and graphs; <iframed> into the html page of the individual activity (html within html)
    src1 = url_for('static', filename=f'charts/{user_id}_{activity_id}_hr_pie.html')
    src2 = url_for('static', filename=f'charts/{user_id}_{activity_id}_hr_hist.html')
    src3 = url_for('static', filename=f'charts/{user_id}_{activity_id}_hr_plot.html')
    src4 = url_for('static', filename=f'charts/{user_id}_{activity_id}_lap_tbl.html')

    return render_template('single_activity_analysis.html', src1=src1, src2=src2, src3=src3, src4=src4)
#endregion - Strava Tasks
#endregion - Strava


if __name__ == '__main__':
    app.secret_key = os.urandom(12)
    app.run(host='0.0.0.0',debug=False, port=8888)