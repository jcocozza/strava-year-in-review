import app_config
from strava_api_throttle import call_api
import pandas as pd
import os
import requests

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

cwd = os.getcwd()
repo_dir = cwd + '/strava-year-in-review'
cwd = repo_dir

approval_link = 'https://www.strava.com/oauth/authorize?client_id=89519&response_type=code&redirect_uri=http://jcocozza.pythonanywhere.com/exchange_token&approval_prompt=force&scope=activity:read'
auth_url = "https://www.strava.com/oauth/token"
activites_url = "https://www.strava.com/api/v3/athlete/activities"

client_id = app_config.client_id
client_secret = app_config.client_secret

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
# This function may need to be modified to accommodate returning users (the refresh payload may not cause the return of a refresh key)
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

# A wrapper function that returns the access token for a user
# Currently, I am not doing anything with the refresh tokens (eventually I will have to save them in a database for returning users)
def get_user_access_token(authorization_code):
    payload = create_payload_auth(client_id, client_secret, authorization_code)
    access_token, refresh_token, athlete_data = get_user_tokens(payload)
    return access_token, refresh_token

# Gets activity data for a user given their access token
def get_user_activity_data(access_token):
    page = 1
    activities = pd.DataFrame()
    print("Pulling Data...")
    try:
        while page <= 3:
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
        # save data to a csv
        activities.to_csv(cwd + '/data/data.csv')
        return activities