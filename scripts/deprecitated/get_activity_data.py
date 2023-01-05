import pandas as pd
import sql_functions
import os
import urllib3
from strava_api_throttle import call_api
import app_config

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

cwd = os.getcwd()
activites_url = "https://www.strava.com/api/v3/athlete/activities"

# Pull the strava data and saves them in a csv
def get_activities():
    page = 1
    activities = pd.DataFrame()
    print("Pulling Data...")
    try:
        while page <= 1: #int(sys.argv[4]):
            param={'per_page': 200, 'page': page}
            data_set = call_api(activites_url, parameter=param).json()

            if (not data_set):
                break
            temp = pd.json_normalize(data_set)
            # Load data into pandas
            activities = pd.concat([activities, temp])
            print("data page: " + str(page) + " pulled")
            page += 1
    except Exception as ex:
        print('Data pull has failed: ', ex)
        exit(1)
    else:
        # save data to a csv
        activities.to_csv(cwd + '/data/data.csv')
        return activities

def upload_file(file):
    sql_functions.upload_data_file_to_remote(data_file=file, table_name='yearly_activity_data')

if __name__ == '__main__':
    act = get_activities()
    upload_file(cwd + '/data/data.csv')


