import get_user_activity_data
import sql_functions
from ast import literal_eval # used to covert an array string to an actual array type e.g. "[0,1,1,1]" --> [0,1,1,1] 
# When I pull from SQL, the (heart rate) stream data will be stored as a string
import flask_app

# General Overview of Process:
# 0) Refresh Strava Data
# 1) Pull previous week's worth of activities
# 2a) Use those activity_id's to pull(from strava) Heart Rate Data for the activities
# 2b) Store Heart Rate Data in data table (elimates the need to repull the data later)
# 2c) Get heart rate data from MySQL
# 3) Data Analysis and manipulation 
# 4) Data Presentation (graphs etc)
# 5) Report Generation
# 6) Email Delivery

# Step 0
flask_app.refresh_data()

# Step 1
def get_previous_week():
    # beginning and end of week tuple
    # In form (YYYY-MM-DD, YYYY-MM-DD) 
    alpha_omega = ()
    return alpha_omega

# need to figure a way to get athlete id
# likely will have an email associated with an account
def get_week_data(beginning_end, athlete_id):
    # Note Query is INCLUSIVE 
    sql = "SELECT * FROM strava_app_activity_data WHERE `athlete.id` = '%s' AND DATE(state_date_local) BETWEEN '%s' AND '%s';" % (athlete_id, beginning_end[0], beginning_end[1])
    week_data = sql_functions.local_sql_to_df(sql)
    return week_data


# Step 2a
activity_id_list = week_data['activitiy.id']
    # need to get HR data -- Need to create a new heartrate_data table in mysql db

# Step 2c
sql = "SELECT * FROM heartrate_data WHERE `activity.id` IN (%s)" % activity_id_list
heartrate_data = sql_functions.local_sql_to_df(sql)

