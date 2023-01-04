from ratelimit import limits, sleep_and_retry
import requests
import urllib3
import app_config
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

FIFTEEN_MINUTES = 900
auth_url = "https://www.strava.com/oauth/token"

# change these to inputs from user
client_id = app_config.client_id
client_secret = app_config.client_secret
refresh_token = app_config.refresh_token


def create_payload(client_id, client_secret, refresh_token):
    payload_info = {
        'client_id': client_id,
        'client_secret': client_secret,
        'refresh_token': refresh_token,
        'grant_type': "refresh_token",
        'f': 'json'}
    return payload_info

# Gets access token for connecting to Strava API
def get_access_token(payload):
    #print("Requesting Token...\n")
    try:
        res = requests.post(auth_url, data=payload, verify=False)
    except Exception as ex:
        print('Unable to get access token: ', ex)
        exit(1)
    else:
        access_token = res.json()['access_token']
        #print("Access Token = {}\n".format(access_token))
        return access_token

payload = create_payload(client_id, client_secret, refresh_token)
access_token = get_access_token(payload)

@sleep_and_retry
@limits(calls=90, period=FIFTEEN_MINUTES)
def call_api(url, parameter=None):
        header = {'Authorization': 'Bearer ' + access_token}
        response = requests.get(url, headers=header, params=parameter)

        if response.status_code != 200:
            raise Exception('API responese: {}'.format(response.status_code))
        return response