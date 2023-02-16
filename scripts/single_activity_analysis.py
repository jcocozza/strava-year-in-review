########## IMPORTS ##########
#region - imports
import plotly.express as px
import pandas as pd
import plotly.graph_objects as go
import sql_functions
import os
from ast import literal_eval
#endregion - imports

########## Setting working directory ##########
cwd = os.getcwd()
repo_dir = cwd + '/strava-year-in-review'
cwd = repo_dir

########## GET DATA ##########
#region - Get Data
# Both functions are self explanatory - pulling data from MySQL Database
# This solely deals with Data from MySQL - No strava involvement

def get_hr_data(activity_id):
    sql = "SELECT * FROM heartrate_data WHERE `activity_id` = '%s'" % activity_id
    heartrate_data = sql_functions.local_sql_to_df(sql)
    return heartrate_data

def get_lap_data(activity_id):
    sql = "SELECT * FROM lap_data WHERE `activity_id` = '%s'" % activity_id
    lap_data = sql_functions.local_sql_to_df(sql)
    return lap_data

#endregion - Get Data
########## END GET DATA ##########

########## DATA MANIPULATION ##########
#region - Data Manipulation

# takes in an array of increasing heart rate zone values and returns zone labels for them
# e.g. [0, 150, 160, 205] will return ['Zone 1', 'Zone 2', 'Zone 3']
# e.g. 0-150 = Zone 1, 150-160 = Zone 2 160-205 = Zone 3
def zones(bin_array):
    # bin_array = [0,150,160,210,250]
    num_zones = len(bin_array) - 1
    # 4 -> 0,1,2,3 -> 1,2,3,4
    labels = [f"Zone {n+1}" for n in range(num_zones)]
    return labels

# Binning heart rate streamed data by zone
def heart_rate_zones(hr_data, bin_array, labels):

    # For some reason, the order of the heartrate data is reversed depending on whether there is a time or distance stream
    if hr_data['series_type'][0] == 'distance':
        series_data = pd.DataFrame.from_dict(data={'hr_series': literal_eval(hr_data['data'][1]), 'dt_series': literal_eval(hr_data['data'][0])})
        series_data.set_index('dt_series')
        series_data['zone'] = pd.cut(series_data['hr_series'], bins=bin_array, labels=labels) # assign each HR value a zone
        series_data.insert(2, "series_type", ['distance'] * len(series_data.index))
    
    if hr_data['series_type'][0] == 'time':
        series_data = pd.DataFrame.from_dict(data={'hr_series': literal_eval(hr_data['data'][0]), 'dt_series': literal_eval(hr_data['data'][1])})
        series_data.set_index('dt_series')
        series_data['zone'] = pd.cut(series_data['hr_series'], bins=bin_array, labels=labels) # assign each HR value a zone
        series_data.insert(2, "series_type", ['time'] * len(series_data.index))

    return series_data

# Bin data based on heart rate zones
def heart_rate_bin_counts(series_data, bin_array, labels):
    count = pd.cut(series_data['hr_series'], bins=bin_array, labels=labels).value_counts().sort_index()

    # Return a dataframe of binned data
    binned_counts = pd.DataFrame({'zones':count.index, 'counts':count}).reset_index(drop=True)

    return binned_counts

#endregion - Data Manipulation
########## END MANIPULATION ##########

########## PLOTS ##########
#region - Plots

# Creates a pie chart, histogram of heart rate data amounts; broken down by zone; include user_id to save files properly
def heart_rate_zone_plots(binned_counts, activity_id, user_id=None):
    pie = px.pie(binned_counts, values='counts', labels='zones',names='zones', title='Heart Rate Zone Data')
    hist = px.histogram(binned_counts, x="zones", y="counts", hover_data=binned_counts.columns, title='Zone Distribution')

    hist.update_layout(yaxis_title="amount in zone (arbritary units)")

    if user_id:
        pie.write_html(cwd + f'/scripts/static/charts/{user_id}_{activity_id}_hr_pie.html')
        hist.write_html(cwd + f'/scripts/static/charts/{user_id}_{activity_id}_hr_hist.html')
    else:
        pie.write_html(cwd + '/scripts/static/charts/hr_pie.html')
        hist.write_html(cwd + '/scripts/static/charts/hr_hist.html')

    return None
    #return pie, hist

# Creates a plot of heartrate data based on series data(either distance or time); include user_id to save files properly
def heart_rate_data_plot(series_data, lap_data, activity_id, user_id=None):
    fig = px.line(series_data, x="dt_series", y="hr_series", title='Heart Rate Data', color_discrete_sequence = ['red'])

    if series_data['series_type'][0] == 'distance':
        # Add Laps to heart rate graph
        lap_start_dist = 0
        for i, (name, begin, end, lap_dist) in enumerate(zip(lap_data['name'], lap_data['start_index'], lap_data['end_index'], lap_data['distance'])):
            lap_end_dist = lap_start_dist + lap_dist
            if i % 2 == 0:
                color = 'blue'
            else:
                color = 'green'
            #fig.add_vrect(x0=begin, x1=end, line_width=0, fillcolor=color, opacity=0.2, annotation_text=name)
            fig.add_vrect(x0=lap_start_dist, x1=lap_end_dist, line_width=0, fillcolor=color, opacity=0.2, annotation_text=name)

            lap_start_dist = lap_end_dist

    if series_data['series_type'][0] == 'time':
        # Add Laps to heart rate graph
        for i, (name, begin, end) in enumerate(zip(lap_data['name'], lap_data['start_index'], lap_data['end_index'])):
            if i % 2 == 0:
                color = 'blue'
            else:
                color = 'green'
            fig.add_vrect(x0=begin, x1=end, line_width=0, fillcolor=color, opacity=0.2, annotation_text=name)

    fig.update_layout(yaxis_title="Heart Rate (BPM)")

    if user_id:
        fig.write_html(cwd + f'/scripts/static/charts/{user_id}_{activity_id}_hr_plot.html')
    else:
        fig.write_html(cwd + '/scripts/static/charts/hr_plot.html')

    return None
    #return fig

#Generates a table of lap activity data; include user_id to save files properly
def activity_lap_data_table(lap_data, activity_id, user_id=None):
    tbl = go.Figure(data=[go.Table(
    header=dict(values=['name','distance(meters)', 'moving time(seconds)', 'elevation gain(meters)', 'average speed(mph)', 'average heartrate(bpm)', 'max heartrate(bpm)'],
                fill_color='paleturquoise',
                align='left'),
    cells=dict(values=[lap_data.name, lap_data.distance, lap_data.moving_time, lap_data.total_elevation_gain, lap_data.average_speed, lap_data.average_heartrate, lap_data.max_heartrate],
               fill_color='lavender',
               align='left'))
    ])

    tbl.update_layout(title_text='Laps taken during activity')

    if user_id:
        tbl.write_html(cwd + f'/scripts/static/charts/{user_id}_{activity_id}_lap_tbl.html')
    else:
        tbl.write_html(cwd + '/scripts/static/charts/lap_tbl.html')

    return None
#endregion - Plots
########## END PLOTS ##########


########## DO ANALYSIS ##########
# creates all plots/tables for an individual activity
def do_activity_analysis(activity_id, user_id, bin_array):
    
    # Get data
    hr_data = get_hr_data(activity_id)
    lap_data = get_lap_data(activity_id)
    labels = zones(bin_array)

    # Manipulate/organize data
    series_data = heart_rate_zones(hr_data, bin_array, labels)
    binned_counts = heart_rate_bin_counts(series_data, bin_array, labels)

    # Plots
    heart_rate_zone_plots(binned_counts, activity_id, user_id)
    heart_rate_data_plot(series_data, lap_data, activity_id, user_id)
    activity_lap_data_table(lap_data, activity_id, user_id)

    return None



