from genericpath import exists
import pandas as pd
import sqlalchemy
import pymysql
import urllib
from datetime import datetime, timedelta
from sshtunnel import SSHTunnelForwarder
import app_config

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

# connect to a remote database via ssh
# note, user requires permissions to connect and use the database
# returns a SQLALCHEMY engine connection
def remote_engine_connection(engine_string, ip_to_connect, user, password, port=22):
    server =  SSHTunnelForwarder(
     (ip_to_connect, port),
     ssh_password=password,
     ssh_username=user,
     remote_bind_address=('localhost', 3306)) # assume that will connect to the local host (the bind address)

    server.start()
    try:
        print('Connecting to engine...')
        engine = sqlalchemy.create_engine(engine_string)
    except Exception as ex:
        print('Unable to create engine connection: ', ex)
        exit(1)
    else:
        print('engine created successfully')
        server.stop()
        return engine

# set metadata for upload to a table in the database
# see https://www.codepowered.com/manuals/SQLAlchemy-0.6.9-doc/html/dialects/mysql.html for more help
# metadata that can be used with sqlalchemy and mysql: 
from sqlalchemy.dialects.mysql import \
        BIGINT, BINARY, BIT, BLOB, BOOLEAN, CHAR, DATE, \
        DATETIME, DECIMAL, DECIMAL, DOUBLE, ENUM, FLOAT, INTEGER, \
        LONGBLOB, LONGTEXT, MEDIUMBLOB, MEDIUMINT, MEDIUMTEXT, NCHAR, \
        NUMERIC, NVARCHAR, REAL, SET, SMALLINT, TEXT, TIME, TIMESTAMP, \
        TINYBLOB, TINYINT, TINYTEXT, VARBINARY, VARCHAR, YEAR
# ex:
table_metadata = {
    '<column_name>':DATETIME(),
    '<column_name>':DECIMAL(),
    '<column_name>':LONGTEXT(), 
}  

# leverages pandas' to_sql function, see: https://pandas.pydata.org/docs/reference/api/pandas.DataFrame.to_sql.html 
# uploads a pandas dataframe to a table 
# By default, will replace the table. Change the if_exists if this is not desired
# can optionally include metadata, or let pandas do it for you
# returns nothing
def df_to_local_sql(df, table_name, metadata=None):
    string = generate_engine_string(app_config.db_user, app_config.db_password, app_config.db_host, app_config.db_name)
    connection = engine_connection(string)

    if 'start_date' in df:
            df['start_date'] = [datetime.strptime(x, '%Y-%m-%dT%H:%M:%SZ') for x in df['start_date']]
            df['start_date_local'] = [datetime.strptime(x, '%Y-%m-%dT%H:%M:%SZ') for x in df['start_date_local']]
    try:
        print('Beginning data upload...')
        df.to_sql(name=table_name, con=connection, if_exists='replace', dtype=metadata, index=False)
    except Exception as ex:
        print('Data upload failed:', ex)
        exit(1)
    else:
        print('Data upload successful')

# leverages pandas' to_sql function, see: https://pandas.pydata.org/docs/reference/api/pandas.DataFrame.to_sql.html 
# uploads a pandas dataframe to a table 
# By default, will replace the table. Change the if_exists if this is not desired
# can optionally include metadata, or let pandas do it for you
# returns nothing
def df_to_remote_sql(df, table_name, metadata=None):
    string = generate_engine_string(app_config.db_user, app_config.db_password, app_config.db_host, app_config.db_name)
    connection = remote_engine_connection(
        engine_string=string,
        ip_to_connect=app_config.db_host, 
        user=app_config.remote_user, 
        password=app_config.remote_password, 
        port=22)

    if 'start_date' in df:
            df['start_date'] = [datetime.strptime(x, '%Y-%m-%dT%H:%M:%SZ') for x in df['start_date']]
            df['start_date_local'] = [datetime.strptime(x, '%Y-%m-%dT%H:%M:%SZ') for x in df['start_date_local']]
    try:
        print('Beginning data upload...')
        df.to_sql(name=table_name, con=connection, if_exists='replace', dtype=metadata, index=False)
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

# uploads a file to a table in a database(per the connection)
# essentiall a wrapper for df_to_remote_sql
# provide metadata for the file/table
# returns nothing
def upload_data_file_to_remote(data_file, table_name, file_metadata=None):
    # file that contains data
    df = pd.read_csv(data_file)
    # upload file
    df_to_remote_sql(df, table_name, metadata=file_metadata) 

# place SQL Queries relevant to your data in here, then they can be easily accessed
# used in sql_to_df to query data
query_library = {
    'primary_query': """SELECT * FROM <table_name>"""}

# tell pandas which columns to parse as dates, and how to parse them
date_parse = {
    '<column_name>': '%Y-%m-%d %H:%M:%SZ',
}

# leverages pandas' read_sql function, see: https://pandas.pydata.org/docs/reference/api/pandas.read_sql.html?highlight=read_sql#pandas.read_sql 
# returns a dataframe of queried SQL data
# see query_library and date_parse
# returns a dataframe
def local_sql_to_df(query):
    string = generate_engine_string(app_config.db_user, app_config.db_password, app_config.db_host, app_config.db_name)
    connection = engine_connection(string)

    print('Querying SQL Data...')
    try:
        df = pd.read_sql(query, con=connection, parse_dates=date_parse)
    except Exception as ex:
        print('Failed to get data: ', ex)
        exit(1)
    else:
        print('Data Successfully Queried...')
        return df

# leverages pandas' read_sql function, see: https://pandas.pydata.org/docs/reference/api/pandas.read_sql.html?highlight=read_sql#pandas.read_sql 
# returns a dataframe of queried SQL data
# see query_library and date_parse
# returns a dataframe
def remote_sql_to_df(query):
    string = generate_engine_string(app_config.db_user, app_config.db_password, app_config.db_host, app_config.db_name)
    connection = remote_engine_connection(
        engine_string=string,
        ip_to_connect=app_config.db_host, 
        user=app_config.remote_user, 
        password=app_config.remote_password, 
        port=22)

    print('Querying SQL Data...')
    try:
        df = pd.read_sql(query, con=connection, parse_dates=date_parse)
    except Exception as ex:
        print('Failed to get data: ', ex)
        exit(1)
    else:
        print('Data Successfully Queried...')
        return df
