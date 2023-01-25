import get_user_activity_data
import sql_functions
from ast import literal_eval # used to covert an array string to an actual array type e.g. "[0,1,1,1]" --> [0,1,1,1]
# When I pull from SQL, the (heart rate) stream data will be stored as a string
import flask_app
import pandas as pd
import os
import sqlalchemy
import app_config
import plotly.express as px
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

########## GET DATA ##########
#region 
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
    activity_id_list = week_data['id']
    refresh_token = sql_functions.get_refresh_token(user_id=user_id)
    access_token = get_user_activity_data.returning_user_access_token(refresh_token) # getting access token

    # Step 2b
    # need to append activity id to this dataframe
    hr_data_frame = pd.DataFrame()
    for act in activity_id_list:
        temp_hr_df = get_user_activity_data.get_heart_rate_activity_data(activity_id=act,access_token=access_token, user_id=user_id)
        hr_data_frame = pd.concat([hr_data_frame, temp_hr_df])

    hr_data_frame.to_csv(cwd + '/data/' + str(user_id) + '_hr_data.csv')

    file_path = cwd + '/data/' + str(user_id) + '_hr_data.csv'
    metadata={
        "data":sqlalchemy.dialects.mysql.LONGTEXT(),
        "type":sqlalchemy.dialects.mysql.VARCHAR(225)}
    sql_functions.upload_data_file_to_local(file_path, 'heartrate_data', metadata)

    # Step 2c
    heartrate_data = pd.DataFrame()
    t = tuple(activity_id_list)
    sql = "SELECT * FROM heartrate_data WHERE `activity_id` IN {}".format(t)
    heartrate_data = sql_functions.local_sql_to_df(sql)
    return heartrate_data

def get_timeinterval_lap_data(week_data, user_id):
    activity_id_list = week_data['id']
    refresh_token = sql_functions.get_refresh_token(user_id=user_id)
    access_token = get_user_activity_data.returning_user_access_token(refresh_token) # getting access token

    lap_data_frame = pd.DataFrame()
    for act in activity_id_list:
        temp_lap_df = get_user_activity_data.get_activity_laps(activity_id=act,access_token=access_token, user_id=user_id)
        lap_data_frame = pd.concat([lap_data_frame, temp_lap_df])

    lap_data_frame.to_csv(cwd + '/data/' + str(user_id) + '_hr_data.csv')

    file_path = cwd + '/data/' + str(user_id) + '_hr_data.csv'
    metadata={
        "data":sqlalchemy.dialects.mysql.LONGTEXT(),
        "type":sqlalchemy.dialects.mysql.VARCHAR(225)}
    sql_functions.upload_data_file_to_local(file_path, 'lap_data', metadata)

    lap_data = pd.DataFrame()
    t = tuple(activity_id_list)
    sql = "SELECT * FROM lap_data WHERE `activity_id` IN {}".format(t)
    lap_data = sql_functions.local_sql_to_df(sql)
    return lap_data

#endregion
########## END GET DATA ##########

########## DATA ANALYSIS ##########
#region 

# Total distance in a given set of activities
def total_distance(activity_data):
    return sum(activity_data['distance'])
# Average distance in a given set of activities over a given time period
def average_distance(activity_data, time_interval):
    return total_distance(activity_data)/time_interval

# Total time in a given set of activities
def total_time(activity_data):
    return sum(activity_data['moving_time'])
# Average time in a given set of activities over a given time period
def average_time(activity_data, time_interval)    :
    return total_time(activity_data)/time_interval

def activity_table(activity_data):
    tbl = activity_data[['name', 'distance', 'moving_time', 'total_elevation_gain', 'type', 'average_speed', 'average_heartrate']]
    return tbl.to_html()

def zone_data(heartrate_data, bin_array, labels):
    hr_array = []
    dt_array = []
    for row in heartrate_data:
        hr_array.append(literal_eval(heartrate_data['data'][1]))
    
    #hr_df = pd.DataFrame(hr_array, columns=['hr_series']) # NEED TO FIX THIS-- pandas is trying to make each elm in array as a column instead of 1 col
    hr_df = pd.DataFrame({'hr_series': hr_array})
    count = pd.cut(hr_df['hr_series'], bins=bin_array, labels=labels).value_counts().sort_index()
    binned_counts = pd.DataFrame({'zones':count.index, 'counts':count}).reset_index(drop=True)

    return binned_counts

#endregion
########## END DATA ANALYSIS ##########

########## PLOTS ##########
#region
def heart_rate_zone_plots(binned_counts):
    pie = px.pie(binned_counts, values='counts', labels='zones',names='zones', title='Heart Rate Zone Data')
    hist = px.histogram(binned_counts, x="zones", y="counts", hover_data=binned_counts.columns, title='Zone Distribution')

    pie.write_html(cwd + '/scripts/static/charts/weekly_hr_pie.html')
    hist.write_html(cwd + '/scripts/static/charts/weekly_hr_hist.html')
    return None

def mileage_graph(activity_data):
    fig = px.bar(activity_data, x='start_data_local', y='distance', color='type')
    fig.write_html(cwd + '/scripts/static/charts/weekly_mileage_bar.html')
    return None

def time_graph(activity_data):
    fig = px.bar(activity_data, x='start_data_local', y='moving_time', color='type')
    fig.write_html(cwd + '/scripts/static/charts/weekly_time_bar.html')
    return None

#endregion
########## END PLOTS ##########


# Amalgamation
def main():
    #flask_app.refresh_data()

    # get_previous_week()
    alpha_omega = ('2022-11-28', '2022-12-04') # Nov 28 - Dec 4
    week_act_data = get_week_activity_data(alpha_omega, app_config.athlete_id)
    weekly_hr_data = get_week_heartrate_data(week_act_data, app_config.user_id)
    weekly_lap_data = get_timeinterval_lap_data(week_act_data,app_config.user_id)

    # temporary to test stuff
    return weekly_lap_data

if __name__ == '__main__':
    data = main()




