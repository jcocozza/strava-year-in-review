########## IMPORTS ##########
#region - imports
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
from flask import url_for
#endregion - imports
########## END IMPORTS ##########

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

########## Setting working directory ##########
cwd = os.getcwd()
repo_dir = cwd + '/strava-year-in-review'
cwd = repo_dir

########## GET DATA - From MySQL ##########
#region - Get Data

# Gets data between a time interval tuple, beginning_end
# beginning_end = ('YYYY-MM-DD','YYYY-MM-DD')
def get_week_activity_data(beginning_end, athlete_id):
    # Note Query is INCLUSIVE
    sql = "SELECT * FROM strava_app_activity_data WHERE `athlete.id` = '%s' AND DATE(start_date_local) BETWEEN '%s' AND '%s';" % (athlete_id, beginning_end[0], beginning_end[1])
    week_data = sql_functions.local_sql_to_df(sql)
    return week_data

# Given some activity data pull the heart rate data for those activities
# Pulls FROM strava and uploads to MySQL database
def get_week_heartrate_data(week_data):
    activity_id_list = week_data['id']

    if len(activity_id_list) == 1:
        t = activity_id_list[0]
        sql = f"""SELECT hrd.activity_id, saad.`type` AS activity_type, hrd.`type` AS stream_type, hrd.series_type, hrd.`data`
                FROM heartrate_data hrd
                INNER JOIN strava_app_activity_data saad
                ON saad.id = hrd.activity_id
                WHERE hrd.activity_id = {t}"""
    else:
        t = tuple(activity_id_list)
        sql = """SELECT hrd.activity_id, saad.`type` AS activity_type, hrd.`type` AS stream_type, hrd.series_type, hrd.`data`
        FROM heartrate_data hrd
        INNER JOIN strava_app_activity_data saad
        ON saad.id = hrd.activity_id
        WHERE hrd.activity_id IN {}""".format(t)

    heartrate_data = sql_functions.local_sql_to_df(sql)

    # interpret literally:
    heartrate_data['data'] = [literal_eval(x) for x in heartrate_data['data']]

    return heartrate_data

def get_timeinterval_lap_data(week_data):
    activity_id_list = week_data['id']

    if len(activity_id_list) == 1:
        t = activity_id_list[0]
        sql = f"SELECT * FROM lap_data WHERE `activity_id` = {t}"
    else:
        t = tuple(activity_id_list)
        sql = "SELECT * FROM lap_data WHERE `activity_id` IN {}".format(t)
    lap_data = sql_functions.local_sql_to_df(sql)
    return lap_data

#endregion
########## END GET DATA - From MySQL ##########

########## DATA ANALYSIS ##########
#region - data analysis

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
def average_time(activity_data, time_interval):
    return total_time(activity_data)/time_interval

# will return a link for a given activity_id
def generate_link(activity_id):
    #link = url_for('activity_analysis', id=activity_id) -- try this in the future so we don't have to hard code anything
    link = f'https://jcocozza.pythonanywhere.com/strava/weekly_summary/activity_analysis?id={activity_id}'
    return link

# returns amount spend in each zone
# This function will likely be depreciated very soon
def zone_data(heartrate_data, bin_array, labels):
    hr_array = []

    if heartrate_data['series_type'][0] == 'distance':
        for row in heartrate_data:
            hr_array = hr_array + literal_eval(heartrate_data['data'][1])
    if heartrate_data['series_type'][0] == 'time':
        for row in heartrate_data:
            hr_array = hr_array + literal_eval(heartrate_data['data'][0])
    '''
    for row in heartrate_data:
        if heartrate_data['series_type'][0] == 'distance':
            hr_array = hr_array + literal_eval(heartrate_data['data'][1])
        if heartrate_data['series_type'][0] == 'time':
            hr_array = hr_array + literal_eval(heartrate_data['data'][0])
    '''
    hr_df = pd.DataFrame({'hr_series': hr_array})

    count = pd.cut(hr_df['hr_series'], bins=bin_array, labels=labels).value_counts().sort_index()
    binned_counts = pd.DataFrame({'zones':count.index, 'counts':count}).reset_index(drop=True)

    return binned_counts

# expand heartrate data so that each element of an array of HR data has its own row (yes, this creates a ton of rows)
def explode_hr_data(heartrate_data, bin_array, labels):
    explode_hr_data = heartrate_data.explode('data')

    exploded = explode_hr_data.loc[explode_hr_data['stream_type'] == 'heartrate'] # only bother with the heartrate data stream
    exploded['zone'] = pd.cut(exploded['data'], bins=bin_array, labels=labels) # set zones for each heart rate value
    return exploded

# bin data by hr_bins, if specified can returned data for a given activity_type
def bin_data(exploded_hr_data, bin_array, labels, activity_type=None):
    if activity_type:
        df = exploded_hr_data.loc[exploded_hr_data['activity_type'] == activity_type] #
        counts = pd.cut(df['data'], bins=bin_array, labels=labels).value_counts().sort_index()
        binned_counts = pd.DataFrame({'zones':counts.index, 'counts':counts}).reset_index(drop=True)
        return binned_counts
    else:
        counts = pd.cut(exploded_hr_data['data'], bins=bin_array, labels=labels).value_counts().sort_index()
        binned_counts = pd.DataFrame({'zones':counts.index, 'counts':counts}).reset_index(drop=True)
        return binned_counts

#endregion - data analysis
########## END DATA ANALYSIS ##########

########## PLOTS ##########
#region
def heart_rate_zone_plots(exploded_hr_data, bin_array, labels, user_id=None):

    total_bin = bin_data(exploded_hr_data, bin_array, labels)
    pie = px.pie(total_bin, values='counts', labels='zones',names='zones', title='Heart Rate Zone Data')

    update_menus = [] # the ability to break down by activity_type
    buttons = [
        {
            'method':'restyle',
            'label':'All',
            'args':[{'values': [bin_data(exploded_hr_data, bin_array, labels)['counts']]},]
        }]
    for activity_type in exploded_hr_data['activity_type'].unique():
        b = {
                'method':'restyle',
                'label':activity_type,
                'args':[{'values': [bin_data(exploded_hr_data, bin_array, labels, activity_type=activity_type)['counts']]},]
            }
        buttons.append(b)
    update_menus.append({'buttons':buttons})

    pie.update_layout(updatemenus=update_menus)

    hist = px.histogram(total_bin, x="zones", y="counts", hover_data=total_bin.columns, title='Zone Distribution')

    update_menus2 = [] # the ability to break down by activity_type
    buttons2 = [
        {
            'method':'restyle',
            'label':'All',
            'args':[{'y': [bin_data(exploded_hr_data, bin_array, labels)['counts']]},]
        }]
    for activity_type in exploded_hr_data['activity_type'].unique():
        b2 = {
                'method':'restyle',
                'label':activity_type,
                'args':[{'y': [bin_data(exploded_hr_data, bin_array, labels, activity_type=activity_type)['counts']]},]
            }
        buttons2.append(b2)
    update_menus2.append({'buttons':buttons2})

    hist.update_layout(updatemenus=update_menus2)

    if user_id:
        pie.write_html(cwd + f'/scripts/static/charts/{user_id}_weekly_hr_pie.html')
        hist.write_html(cwd + f'/scripts/static/charts/{user_id}_weekly_hr_hist.html')
    else:
        pie.write_html(cwd + '/scripts/static/charts/weekly_hr_pie.html')
        hist.write_html(cwd + '/scripts/static/charts/weekly_hr_hist.html')
    return None

def mileage_graph(activity_data, user_id=None):
    fig = px.bar(activity_data, x='start_date_local', y='distance', color='type')
    if user_id:
        fig.write_html(cwd + f'/scripts/static/charts/{user_id}_weekly_mileage_bar.html')
    else:
        fig.write_html(cwd + '/scripts/static/charts/weekly_mileage_bar.html')
    return None

def time_graph(activity_data, user_id=None):
    fig = px.bar(activity_data, x='start_date_local', y='moving_time', color='type')

    if user_id:
        fig.write_html(cwd + f'/scripts/static/charts/{user_id}_weekly_time_bar.html')
    else:
        fig.write_html(cwd + '/scripts/static/charts/weekly_time_bar.html')
    return None

def activity_table(activity_data):
    #tbl = activity_data[['name', 'distance', 'moving_time', 'total_elevation_gain', 'type', 'average_speed', 'average_heartrate']]

    html =  """<table>
                <tr>
                    <th>name</th>
                    <th>date</th>
                    <th>distance</th>
                    <th>moving_time</th>
                    <th>total_elevation_gain</th>
                    <th>type</th>
                    <th>average_speed</th>
                    <th>average_heartrate</th>
                </tr>"""

    for id,date,name,dist,mt,teg,type,avg_speed,avg_hr in zip(activity_data['id'], activity_data['start_date_local'], activity_data['name'], activity_data['distance'], activity_data['moving_time'], activity_data['total_elevation_gain'], activity_data['type'], activity_data['average_speed'], activity_data['average_heartrate']):
        link = generate_link(id)

        html += f""" <tr>
                         <td><a href={link}>{name}</a></td>
                         <td>{date}</td>
                         <td>{dist}</td>
                         <td>{mt}</td>
                         <td>{teg}</td>
                         <td>{type}</td>
                         <td>{avg_speed}</td>
                         <td>{avg_hr}</td>
                        </tr>"""
    html += """</table>"""

    return html #tbl.to_html()

#endregion
########## END PLOTS ##########

########## MAIN ##########
#region - main

def run_all(week_tuple, athlete_id, bin_array, labels, user_id, duration=7):
    ########## GETTING ACTIVITY DATA ##########
    week_activity_data = get_week_activity_data(week_tuple, athlete_id)

    if week_activity_data.empty: # If there is no data in the time frame then there is nothing we can do.
        return 'There are no detected activites for this week. Consider refreshing strava data if you think this is a mistake.'

    ########## Make sure MySQL DB is up to date for HR and lap data ##########
    get_user_activity_data.api_to_mysql_heartrate_lap_data(week_activity_data, user_id)

    ########## GETTING LAP/HR DATA ##########
    week_heartrate_data = get_week_heartrate_data(week_activity_data)
    week_lap_data = get_timeinterval_lap_data(week_activity_data)

    ########## DATA ANALYSIS ##########
    total_mileage = total_distance(week_activity_data)
    avg_mileage = average_distance(week_activity_data, duration)
    tot_time = total_time(week_activity_data)
    avg_time = average_time(week_activity_data, duration)

    act_table = activity_table(week_activity_data)
    exploded_hr_data = explode_hr_data(week_heartrate_data, bin_array, labels)

    ########## PLOTS ##########
    hr_plots = heart_rate_zone_plots(exploded_hr_data, bin_array, labels, user_id)
    mileage = mileage_graph(week_activity_data, user_id)
    time = time_graph(week_activity_data, user_id)

    return act_table
#endregion - main
########## END MAIN ##########
