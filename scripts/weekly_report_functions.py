import get_user_activity_data
import sql_functions
from ast import literal_eval # used to covert an array string to an actual array type e.g. "[0,1,1,1]" --> [0,1,1,1] 
# When I pull from SQL, the (heart rate) stream data will be stored as a string
import flask_app
import pandas as pd
import os
import sqlalchemy
import app_config
# General Overview of Process:
# 0) Refresh Strava Data
# 1) Pull previous week's worth of activities
# 2) Heart Rate Data
#   2a) Use those activity_id's to pull(from strava) Heart Rate Data for the activities
#   2b) Store Heart Rate Data in data table (elimates the need to repull the data later)
#   2c) Get heart rate data from MySQL
# 3) Data Analysis and manipulation 
# 4) Data Presentation (graphs etc)
# 5) Report Generation
# 6) Email Delivery

cwd = os.getcwd()
repo_dir = cwd + '/strava-year-in-review'
cwd = repo_dir

# Step 0 - run this: 
#flask_app.refresh_data()

# Step 1
def get_previous_week():
    # beginning and end of week tuple
    # In form (YYYY-MM-DD, YYYY-MM-DD) 
    alpha_omega = ()
    return alpha_omega

# need to figure a way to get athlete id
# likely will have an email associated with an account
def get_week_activity_data(beginning_end, athlete_id):
    # Note Query is INCLUSIVE 
    sql = "SELECT * FROM strava_app_activity_data WHERE `athlete.id` = '%s' AND DATE(start_date_local) BETWEEN '%s' AND '%s';" % (athlete_id, beginning_end[0], beginning_end[1])
    week_data = sql_functions.local_sql_to_df(sql)
    return week_data

# Step 2
def get_week_heartrate_data(week_data, user_id):
    # Step 2a
    activity_id_list = week_data['activitiy.id']
    refresh_token = sql_functions.get_refresh_token(user_id=user_id)
    access_token = get_user_activity_data.returning_user_access_token(refresh_token) # getting access token

    # Step 2b
    hr_data_frame = pd.DataFrame()
    for act in activity_id_list:
        temp_hr_df = get_user_activity_data.get_heart_rate_activity_data(activity_id=act,access_token=access_token, user_id=user_id)
        hr_data_frame = pd.concat(hr_data_frame, temp_hr_df)
    
    # Upload Heart Rate data - Need to create a new heartrate_data table in mysql db
    file_path = cwd + '/data/' + str(user_id) + '_lap_data.csv'
    metadata={"data":sqlalchemy.dialects.mysql.LONGTEXT()}
    sql_functions.upload_data_file_to_local(file_path, 'heartrate_data', metadata)
    
    # Step 2c
    sql = "SELECT * FROM heartrate_data WHERE `activity.id` IN (%s)" % activity_id_list
    heartrate_data = sql_functions.local_sql_to_df(sql)
    
    return heartrate_data

# Step 3




# Amalgamation
def main():
    flask_app.refresh_data()
    
    # get_previous_week()
    alpha_omega = ('2022-11-28', '2022-12-04') # Nov 28 - Dec 4
    week_act_data = get_week_activity_data(alpha_omega, app_config.athlete_id)
    weekly_hr_data = get_week_heartrate_data(week_act_data, app_config.user_id)

    # temporary to test stuff
    return weekly_hr_data





