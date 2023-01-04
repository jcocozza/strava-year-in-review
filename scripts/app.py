from flask import Flask, render_template, Markup
import sql_functions
import get_activity_data
import os
import sys
from io import StringIO
cwd = os.getcwd()

class Capturing(list):
    def __enter__(self):
        self._stdout = sys.stdout
        sys.stdout = self._stringio = StringIO()
        return self
    def __exit__(self, *args):
        self.extend(self._stringio.getvalue().splitlines())
        del self._stringio    # free up some memory
        sys.stdout = self._stdout

app = Flask(__name__)

@app.route('/')
def welcome_page():
    return render_template('home.html')

@app.route('/strava_connection')
def strava_connection():
    with Capturing() as output:
        get_activity_data.get_activities()
        get_activity_data.upload_file(cwd + '/data/data.csv')
    return render_template('get_data.html', my_output=output)

@app.route('/summary_data')
def summarize():
    query = """SELECT SUM((ad.distance/1609.344)) AS DIST, SUM((ad.moving_time/60)) AS mov_time, SUM((ad.moving_time/60))/SUM((ad.distance/1609.344)) AS average_speed, SUM(ad.total_elevation_gain) AS total_elevation_gain 
    FROM yearly_activity_data ad
    WHERE ad.`type` = "Run" AND YEAR(start_date) = 2022;"""

    data = sql_functions.remote_sql_to_df(query)
    return render_template('summary.html', data_table=Markup(data.to_html()))

@app.route('/activity_list')
def activity_list():
    query = """SELECT ad.name, ad.id, (ad.distance/1609.344) AS distance, (ad.moving_time/60) AS moving_time, (1609.344/(ad.average_speed*60)) AS average_speed, ad.start_date_local
    FROM yearly_activity_data ad 
    WHERE ad.`type` = "Run" AND YEAR(start_date) = 2022;"""

    data = sql_functions.remote_sql_to_df(query)
    return render_template('activity_list.html', data_table=Markup(data.to_html()))

if __name__ == '__main__':
    app.run(debug = True)