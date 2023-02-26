########## IMPORTS ##########
# region - imports
import weekly_report_functions
import single_activity_analysis
import get_user_activity_data
from datetime import datetime
import os

# endregion - imports
########## END IMPORTS ##########
########## Setting working directory ##########
image_path = os.getcwd() + '/strava-year-in-review/scripts/static/images/'

########## PARAMETERS ##########
# region - params
#bin_array = [0, 150, 160, 205]  # Heart Rate Bins
#user_id = sys.argv[1]  # pass in user_id into script
#athlete_id = sys.argv[2]  # pass in athlete_id into script

#start_date = sys.argv[3]  # pass start_date into script (%Y-%m-%d)
#end_date = sys.argv[4]  # pass end_date into script (%Y-%m-%d)

# endregion - params
########## END PARAMETERS ##########

def create_report(bin_array, user_id, athlete_id, start_date, end_date):
    # Labels for the bins
    labels = single_activity_analysis.zones(bin_array)
    ########## SET UP INFORMATION ##########
    # region - set up
    starting_datetime = datetime.strptime(
        start_date, "%Y-%m-%d")  # convert date string to datetime
    ending_datetime = datetime.strptime(
        end_date, "%Y-%m-%d")  # convert date string to datetime
    delta = ending_datetime - starting_datetime  # time delta between start and end
    duration = delta.days + 1  # The interval we are doing analysis over
    week_tuple = (start_date, end_date)
    header = f'Summary for {start_date} to {end_date}'

    # Refresh Activity Data
    get_user_activity_data.refresh_activity_data(user_id)

    # Get activity data for the time interval
    interval_activity_data = weekly_report_functions.get_week_activity_data(
        week_tuple, athlete_id)

    # Ensure that lap/hr data is upto date in mysql-db
    get_user_activity_data.api_to_mysql_heartrate_lap_data(
        interval_activity_data, user_id)

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
    src1 = hr_plots[0].write_html(image_path + f"{user_id}_hr1.html")
    src2 = hr_plots[1].write_html(image_path + f"{user_id}_hr2.html")
    src3 = mileage.write_html(image_path + f"{user_id}_mileage.html")
    src4 = time.write_iwrite_htmlmage(image_path + f"{user_id}_time.html")

    # endregion - plots
    ########## END PLOTS ##########

    ########## HTML ##########
    #region - html
    email_text = "email report"

    email_html = f"""
    <!DOCTYPE html>
    <html lang="en" dir="ltr">
    <head>
        <meta charset="utf-8">
    </head>
    <body>
        <!-- Report content -->
        <script src="https://cdn.plot.ly/plotly-latest.min.js"></script>
        <h1> { header } </h1>

        <h2> Overview: </h2>
        <!-- total_mileage, avg_mileage, tot_time, avg_time -->
            <table border="1">
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

        <br><img src="cid:image1"><br>
        <br><img src="cid:image2"><br>
        <br><img src="cid:image3"><br>
        <br><img src="cid:image4"><br>

        <!-- End Report content -->
    </body>
    </html>"""
    #endregion - html
    ########## HTML ##########
    return email_html, src1, src2, src3, src4







