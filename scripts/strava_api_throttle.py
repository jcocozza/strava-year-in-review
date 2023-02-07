########## IMPORTS ##########
#region - imports
from ratelimit import limits, sleep_and_retry
import os
import requests
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
#endregion - imports
########## END IMPORTS ##########

########## Setting working directory ##########
cwd = os.getcwd()
repo_dir = cwd + '/strava-year-in-review'
cwd = repo_dir

log_path = cwd + "/data/api_log.txt"

########## THROTTLE ##########
#region - Throttle
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

        with open(log_path, 'w') as log:
            log.write('########## START LOG ##########\n')
            log.write(f'API CALL FOR: {url}\n')
            log.write(f'Header: {header}\n')
            if parameter:
                log.write(f'Parameters passed: {parameter}\n')
            log.write(f'Response status code: {response.status_code}\n')
            log.write('########## END LOG ##########\n')
        
        return response
#endregion - Throttle
########## END THROTTLE ##########