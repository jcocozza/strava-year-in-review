########## IMPORTS ##########
#region - imports
from genericpath import exists
import pandas as pd
import sqlalchemy
from sqlalchemy import text
import pymysql
import urllib
from datetime import datetime, timedelta
#from sshtunnel import SSHTunnelForwarder
import app_config
from flask import session
# For handling duplicates
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.sql.expression import Insert
#endregion - imports
########## END IMPORTS ##########

# generates an engine string for connecting to a mysql database
# returns a string
def generate_engine_string(user, password, host, database_name):
    print('Generating engine string...')
    db_password = password
    db_password_quoted = urllib.parse.quote(db_password)
    string = "mysql+pymysql://%s:" % (user,) + db_password_quoted + '@%s/%s' % (host, database_name)
    print('Engine String generated: ', string)
    return string

# creates a sqlalchemy engine connection - connects to a local database
# returns a SQLALCHEMY engine connection
def engine_connection(engine_string):
    try:
        print('Connecting to engine...')
        engine = sqlalchemy.create_engine(engine_string)
    except Exception as ex:
        print('Unable to create engine connection: ', ex)
        exit(1)
    else:
        print('engine created successfully')
        return engine

# Using SQLAlchemy built in features rather than converting to a dataframe
def query_database(query):
    print(f'Querying SQL Data for Query: {query}')
    string = generate_engine_string(app_config.db_user, app_config.db_password, app_config.db_host, app_config.db_name)
    connection = engine_connection(string)

    result = connection.execute(query)
    return result

# Adding refresh token that is generated for a user
def insert_refresh_token(token):
    sql = "UPDATE users SET refresh_token = '%s' WHERE user_id = %s" % (token, session['id'])

    string = generate_engine_string(app_config.db_user, app_config.db_password, app_config.db_host, app_config.db_name)
    connection = engine_connection(string)

    with connection.connect() as conn:
        conn.execute(text(sql))
        print('token inserted successfully')

# Adding athlete_id that is pulled from strava
def insert_athlete_id(athlete_id):
    sql = "UPDATE users SET athlete_id = '%s' WHERE user_id = %s" % (athlete_id, session['id'])

    string = generate_engine_string(app_config.db_user, app_config.db_password, app_config.db_host, app_config.db_name)
    connection = engine_connection(string)

    with connection.connect() as conn:
        conn.execute(text(sql))
        print('athlete_id inserted successfully')

# returns athlete_id stored in user table based on what user is logged in
def get_athlete_id():
    print('Getting athlete_id')
    sql = "SELECT athlete_id FROM users WHERE user_id = %s" % (session['id'],)
    id = local_sql_to_df(sql)['athlete_id'][0]
    return id
'''
# check if an activity is in a table
# returns true if the activity_id is in the table
# otherwise returns false
def check_if_in(activity_id, tbl):
    sql = f'SELECT activity_id FROM {tbl} WHERE activity_id = {activity_id}'
    df = local_sql_to_df(sql)
    return not df.empty

# returns activity_id's not in the table
def activity_id_not_in_list(activity_list, tbl):
    not_in_activity_list = []
    for activity in activity_list:
        if not check_if_in(activity, tbl):
            not_in_activity_list.append(activity)
    return not_in_activity_list
'''
def activity_id_not_in_list(activity_list, tbl):
    sql = f"""SELECT saad.id
                FROM strava_app_activity_data saad
                LEFT JOIN {tbl} hrd
                ON saad.id = hrd.activity_id
                WHERE hrd.activity_id IS NULL;"""

    li = local_sql_to_df(sql)['id'] # get data in activity table, but not in hr table

    not_in_activity_list = list(set(activity_list) & set(li)) # get the data NOT in hr table and that we want to pull
    return not_in_activity_list


# gets a users refresh token
def get_refresh_token(user_id=None):
    if user_id:
        sql = "SELECT refresh_token FROM users WHERE user_id = '%s'" % user_id
    else:
        sql = "SELECT refresh_token FROM users WHERE user_id = '%s'" % (session['id'],)
    data = local_sql_to_df(sql) # get refresh token from db
    refresh_token = data['refresh_token'][0]
    return refresh_token

# leverages pandas' to_sql function, see: https://pandas.pydata.org/docs/reference/api/pandas.DataFrame.to_sql.html
# uploads a pandas dataframe to a table
# By default, will replace the table. Change the if_exists if this is not desired
# can optionally include metadata, or let pandas do it for you
# returns nothing
def df_to_local_sql(df, table_name, metadata=None):

    # adds the word IGNORE after INSERT in sqlalchemy
    # This is a workaround to handle duplicate rows
    # Since id is a primary key in the table schema, duplicates will not be uploaded
    @compiles(Insert)
    def _prefix_insert_with_ignore(insert, compiler, **kw):
        return compiler.visit_insert(insert.prefix_with('IGNORE'), **kw)

    string = generate_engine_string(app_config.db_user, app_config.db_password, app_config.db_host, app_config.db_name)
    connection = engine_connection(string)

    if 'start_date' in df:
            df['start_date'] = [datetime.strptime(x, '%Y-%m-%dT%H:%M:%SZ') for x in df['start_date']]
            df['start_date_local'] = [datetime.strptime(x, '%Y-%m-%dT%H:%M:%SZ') for x in df['start_date_local']]
    try:
        print('Beginning data upload...')
        df.to_sql(name=table_name, con=connection, if_exists='append', dtype=metadata, index=False)
    except Exception as ex:
        print('Data upload failed:', ex)
        exit(1)
    else:
        print('Data upload successful')

# uploads a file to a table in a database(per the connection)
# essentiall a wrapper for df_to_remote_sql
# provide metadata for the file/table
# returns nothing
def upload_data_file_to_local(data_file, table_name, file_metadata=None):
    # file that contains data
    df = pd.read_csv(data_file)
    # upload file
    df_to_local_sql(df, table_name, metadata=file_metadata)

# leverages pandas' read_sql function, see: https://pandas.pydata.org/docs/reference/api/pandas.read_sql.html?highlight=read_sql#pandas.read_sql
# returns a dataframe of queried SQL data
# see query_library and date_parse
# returns a dataframe
def local_sql_to_df(query, parse_dates=None):
    string = generate_engine_string(app_config.db_user, app_config.db_password, app_config.db_host, app_config.db_name)
    connection = engine_connection(string)

    print(f'Querying SQL Data for Query: {query}')
    try:
        df = pd.read_sql(query, con=connection, parse_dates=parse_dates)
    except Exception as ex:
        print('Failed to get data: ', ex)
        exit(1)
    else:
        print('Data Successfully Queried...')
        return df
