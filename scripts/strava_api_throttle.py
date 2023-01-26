########## IMPORTS ##########
#region - imports
from ratelimit import limits, sleep_and_retry
import requests
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
#endregion - imports

# This handles GET calls to the Strava API to get data
# Uses the wrapper to limit calls 

FIFTEEN_MINUTES = 900
auth_url = "https://www.strava.com/oauth/token"

@sleep_and_retry
@limits(calls=90, period=FIFTEEN_MINUTES)
def call_api(url, access_token, parameter=None):
        header = {'Authorization': 'Bearer ' + access_token}
        response = requests.get(url, headers=header, params=parameter)

        if response.status_code != 200:
            raise Exception('API responese: {}'.format(response.status_code))
        return response