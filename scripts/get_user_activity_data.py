########## IMPORTS ##########
#region - imports
import app_config
from strava_api_throttle import call_api
import pandas as pd
import os
import requests
import sql_functions
import sqlalchemy
#endregion - imports
########## END IMPORTS ##########

# A quick overview of how this works:
# The developer needs to create an application through strava
# From this they get a client_id and client_secret
# The application will send a user to a link similar to this:
# https://www.strava.com/oauth/authorize?client_id=89519&response_type=code&redirect_uri=http://localhost:8888/exchange_token&approval_prompt=force&scope=activity:read
# that link will proper the user to grant permissions so the developer can access data
# The link will then foward the user to the redirect_uri. This foward will contain an authorization code in the URL
# From that authorization code the developer can generate an access token by making a POST request to https://www.strava.com/oauth/token
# The post request will return an access token.
# The access token can then be used with a GET request to https://www.strava.com/api/v3/athlete/activities for data

########## Setting working directory ##########
cwd = os.getcwd()
repo_dir = cwd + '/strava-year-in-review'
cwd = repo_dir

########## PARAMETERS ##########
approval_link = 'https://www.strava.com/oauth/authorize?client_id=89519&response_type=code&redirect_uri=http://jcocozza.pythonanywhere.com/strava/exchange_token&approval_prompt=force&scope=activity:read'
auth_url = "https://www.strava.com/oauth/token"
activites_url = "https://www.strava.com/api/v3/athlete/activities"

client_id = app_config.client_id
client_secret = app_config.client_secret


########## TOKENS ##########
#region - tokens
# Used for first time users to get a refresh token and access token
def create_payload_auth(client_id, client_secret, authorization_code):
    payload_info = {
        'client_id': client_id,
        'client_secret': client_secret,
        'code': authorization_code,
        'grant_type': "authorization_code",
        'f': 'json'}
    return payload_info

# Used for returning users to get a new access token
def create_payload_refresh(client_id, client_secret, refresh_token):
    payload_info = {
        'client_id': client_id,
        'client_secret': client_secret,
        'refresh_token': refresh_token,
        'grant_type': "refresh_token",
        'f': 'json'}
    return payload_info

# Gets access and refresh tokens for connecting to Strava API
# This is for first time users who are granting strava access for the first time
def get_user_tokens(payload):
    print("Requesting Token...\n")
    try:
        res = requests.post(auth_url, data=payload, verify=False)
    except Exception as ex:
        print('Unable to get access token: ', ex)
        exit(1)
    else:
        access_token = res.json()['access_token']
        refresh_token = res.json()['refresh_token']
        athlete_data = res.json()['athlete']
        print("Access Token = {}\n".format(access_token))
        print("Refresh Token = {}\n".format(refresh_token))
        return access_token, refresh_token, athlete_data

# For users that have already granted access to strava
def get_user_access_token_from_refresh_token(payload):
    print("Requesting Token...\n")
    try:
        res = requests.post(auth_url, data=payload, verify=False)
    except Exception as ex:
        print('Unable to get access token: ', ex)
        exit(1)
    else:
        access_token = res.json()['access_token']
        print("Access Token = {}\n".format(access_token))
        return access_token

# A wrapper function that returns the access token for a NEW user
def get_user_access_token(authorization_code):
    payload = create_payload_auth(client_id, client_secret, authorization_code)
    access_token, refresh_token, athlete_data = get_user_tokens(payload)
    return access_token, refresh_token, athlete_data

# A wrapper function that returns access token for a RETURNING user
def returning_user_access_token(refresh_token):
    payload = create_payload_refresh(client_id, client_secret, refresh_token)
    access_token = get_user_access_token_from_refresh_token(payload)
    return access_token

#endregion - tokens
########## END TOKENS ##########

########## GETTING DATA ##########
#region - Data From Strava to MySQL

##### Activity Data #####
#region - Activity Data
# Gets activity data for a user given their access token; saves to csv
# Pull at most pages_to_pull; Should be min of 1
def get_user_activity_data(access_token, user_id=None, pages_to_pull=None):
    page = 1
    activities = pd.DataFrame()
    print("Pulling Data...")
    try:
        while page <= pages_to_pull: # dynamic to minimize calls to api
            param={'per_page': 200, 'page': page}
            data_set = call_api(url=activites_url, access_token=access_token, parameter=param).json()

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
        if user_id:
            file_path = cwd + '/data/' + str(user_id) + '_data.csv'
            activities.to_csv(file_path) # save data to a csv
            sql_functions.upload_data_file_to_local(file_path, 'strava_app_activity_data') # upload csv to MySQL
        else:
            activities.to_csv(cwd + '/data/data.csv') # save data to a csv
        return activities

#endregion - Activity Data
##### End Activity Data #####

##### HeartRate Data #####
#region - heartrate data
# Heartrate url for interacting with Strava API to get heartrate streams
def create_hr_url(activity_id):
    hr_url = "https://www.strava.com/api/v3/activities/%s/streams?keys=heartrate&key_by_type=" % (activity_id, )
    return hr_url

# Get 1 activity's worth of heartrate data (per strava policy, can only pull 1 Stream worth of data per API call)
def get_heart_rate_activity_data(activity_id, access_token):
    try:
        hr_url = create_hr_url(activity_id)
        hr_data = call_api(url=hr_url, access_token=access_token).json()
        hr_dataframe = pd.json_normalize(hr_data)
        hr_dataframe.insert(0, "activity_id", [activity_id] * len(hr_dataframe.index))
    except Exception as ex:
        print('Heart Rate data pull has failed: ', ex)
        exit(1)
    else:
        return hr_dataframe

# Given some activity data pull the heart rate data for those activities
# Pulls from strava; saves to csv; uploads to MySQL
def get_heartrate_data_for_activities(activity_data, user_id):
    activity_id_list = activity_data['id'] #list of activities that we need HR data for
    activity_id_list = sql_functions.activity_id_not_in_list(activity_id_list, 'heartrate_data') #list of activities that we don't have HR data for yet

    if not activity_id_list: #if there are no activities we don't have HR data for, then there's nothing else we need to do here
        return None

    refresh_token = sql_functions.get_refresh_token(user_id=user_id)
    access_token = returning_user_access_token(refresh_token) # getting access token

    hr_data_frame = pd.DataFrame()
    for act in activity_id_list:
        temp_hr_df = get_heart_rate_activity_data(activity_id=act,access_token=access_token)
        hr_data_frame = pd.concat([hr_data_frame, temp_hr_df])
    
    file_path = cwd + '/data/' + str(user_id) + '_hr_data.csv'

    hr_data_frame.to_csv(file_path) # save dataframe to csv

    metadata={
        "data":sqlalchemy.dialects.mysql.LONGTEXT(),
        "type":sqlalchemy.dialects.mysql.VARCHAR(225)}
    sql_functions.upload_data_file_to_local(file_path, 'heartrate_data', metadata) # upload csv to MySQL
    return hr_data_frame

#endregion - heartrate data
##### End HeartRate Data #####

##### Lap Data #####
#region - lap data
# Lap url for interacting with Strava API to get lap streams
def create_lap_url(activity_id):
    hr_url = "https://www.strava.com/api/v3/activities/%s/laps" % (activity_id, )
    return hr_url

# Gets Laps for an individual activity; specifiy user_id to save file properly
def get_activity_laps(activity_id, access_token):
    try:
        lap_url = create_lap_url(activity_id)
        lap_data = call_api(url=lap_url, access_token=access_token).json()
        lap_dataframe = pd.json_normalize(lap_data)
        lap_dataframe.insert(0, "activity_id", [activity_id] * len(lap_dataframe.index))
    except Exception as ex:
        print('Lap data pull has failed: ', ex)
        exit(1)
    else:
        return lap_dataframe

# Given some activity data pull the heart rate data for those activities
# Pulls from strava; saves to csv; uploads to MySQL
def get_lap_data_for_activities(activity_data, user_id):
    activity_id_list = activity_data['id'] #list of activities that we need lap data for
    activity_id_list = sql_functions.activity_id_not_in_list(activity_id_list, 'heartrate_data') #list of activities that we don't have lap data for yet

    if not activity_id_list: #if there are no activities we don't have lap data for, then there's nothing else we need to do here
        return None

    refresh_token = sql_functions.get_refresh_token(user_id=user_id)
    access_token = returning_user_access_token(refresh_token) # getting access token

    lap_data_frame = pd.DataFrame()
    for act in activity_id_list:
        temp_lap_df = get_activity_laps(activity_id=act, access_token=access_token)
        lap_data_frame = pd.concat([lap_data_frame, temp_lap_df])

    file_path = cwd + '/data/' + str(user_id) + '_lap_data.csv'

    lap_data_frame.to_csv(file_path)

    metadata={
        "data":sqlalchemy.dialects.mysql.LONGTEXT(),
        "type":sqlalchemy.dialects.mysql.VARCHAR(225)}
    sql_functions.upload_data_file_to_local(file_path, 'lap_data', metadata)

    return lap_data_frame

#endregion - lap data
##### End Lap Data #####

##### Activity List Wrappers #####
#region - meta function

# handles both heartrate data and lap data for a given set of activities
# STRAVA -> CSV -> MySQL
# Saves data to csv and uploads to MySQL
# will not call API for data already in the database
def api_to_mysql_heartrate_lap_data(activity_data, user_id):
    hr_data = get_heartrate_data_for_activities(activity_data, user_id)
    lap_data = get_lap_data_for_activities(activity_data, user_id)
    return None

# pulls the latest Strava activity and saves to MySQL
def refresh_activity_data(user_id):
    refresh_token = sql_functions.get_refresh_token()
    access_token = returning_user_access_token(refresh_token) # getting access token
    data = get_user_activity_data(access_token, user_id, pages_to_pull=1)
    return None

#endregion - meta function
##### END Activity List Wrappers #####

#endregion - Data From Strava to MySQL
########## END GETTING DATA ##########

