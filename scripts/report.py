########## IMPORTS ##########
# region - imports
from plotly.offline import plot
import weekly_report_functions
import single_activity_analysis
import get_user_activity_data
import sys
from datetime import datetime

# endregion - imports
########## END IMPORTS ##########


########## PARAMETERS ##########
# region - params
bin_array = [0, 150, 160, 205]  # Heart Rate Bins
labels = single_activity_analysis.zones(bin_array)  # Labels for the bins
user_id = sys.argv[1]  # pass in user_id into script
athlete_id = sys.argv[2]  # pass in athlete_id into scropty

start_date = sys.argv[3]  # pass start_date into script (%Y-%m-%d)
end_date = sys.argv[4]  # pass end_date into script (%Y-%m-%d)

# endregion - params
########## END PARAMETERS ##########

########## SET UP INFORMATION ##########
# region - set up
starting_datetime = datetime.strptime(
    start_date, "%Y-%m-%d")  # convert date string to datetime
ending_datetime = datetime.strptime(
    end_date, "%Y-%m-%d")  # convert date string to datetime
delta = ending_datetime - starting_datetime  # time delta between start and end
duration = delta.days  # The interval we are doing analysis over
week_tuple = (start_date, end_date)
header = f'Summary for {start_date} to {end_date}'


# Get activity data for the time interval
# Need to refresh activity data too
interval_activity_data = weekly_report_functions.get_week_activity_data(
    week_tuple, athlete_id)
get_user_activity_data.api_to_mysql_heartrate_lap_data(
    interval_activity_data, user_id)  # ensure that lap/hr data is upto date in mysql-db

# Get Lap/HR data for the time interval
interval_heartrate_data = weekly_report_functions.get_week_heartrate_data(
    interval_activity_data)
interval_lap_data = weekly_report_functions.get_timeinterval_lap_data(
    interval_activity_data)

# endregion - set up
########## END SET UP INFORMATION ##########

########## DATA ANALYSIS ##########
# region - analysis
total_mileage = weekly_report_functions.total_distance(interval_activity_data)
avg_mileage = weekly_report_functions.average_distance(
    interval_activity_data, duration)
tot_time = weekly_report_functions.total_time(interval_activity_data)
avg_time = weekly_report_functions.average_time(
    interval_activity_data, duration)
tot_elev = weekly_report_functions.total_elevation_gain(
    interval_activity_data)

exploded_hr_data = weekly_report_functions.explode_hr_data(
    interval_heartrate_data, bin_array, labels)
# endregion - analysis
########## END DATA ANALYSIS ##########


########## PLOTS AND GRAPHS ##########
# region - plots
act_table = weekly_report_functions.activity_table(interval_activity_data)
hr_plots = weekly_report_functions.heart_rate_zone_plots(
    exploded_hr_data, bin_array, labels, user_id)
mileage = weekly_report_functions.mileage_graph(
    interval_activity_data, user_id)
time = weekly_report_functions.time_graph(interval_activity_data, user_id)

# use this to embedded in email
# where fig is the plot to embed

# Generate your plotly figure as fig
src1 = plot(
    hr_plots[0],
    output_type='div',
    include_plotlyjs=True
)
src2 = plot(
    hr_plots[1],
    output_type='div',
    include_plotlyjs=True
)
src3 = plot(
    mileage,
    output_type='div',
    include_plotlyjs=True
)
src4 = plot(
    time,
    output_type='div',
    include_plotlyjs=True
)


# endregion - plots
########## END PLOTS ##########

########## HTML ##########

email_text = "email report"

email_html = f"""
<!DOCTYPE html>
<html lang="en" dir="ltr">
   <head>
      <meta charset="utf-8">
   </head>
   <body>
      <!-- Report content -->
      <h1> { header } </h1>

      <h2> Overview: </h2>
      <!-- total_mileage, avg_mileage, tot_time, avg_time -->
         <table>
            <tr>
               <th>Total Mileage (miles)</th>
               <th>Average Mileage (miles)</th>
               <th>Total Time (hours)</th>
               <th>Average Time (hours)</th>
               <th>Total Elevation Gain (meters)</th>
            </tr>
            <tr>
               <td>{ total_mileage }</td>
               <td>{ avg_mileage }</td>
               <td> { tot_time }</td>
               <td> { avg_time }</td>
               <td> { tot_elev }</td>
            </tr>
         </table>

      <h2> Activites for the week </h2>
      <p> { act_table } </p>

      <h2> Week Summary Graphs</h2>
      
      { src1 }
      { src1 }
      { src1 }
      { src1 }
      <!-- End Report content -->
   </body>
</html>"""
########## HTML ##########






