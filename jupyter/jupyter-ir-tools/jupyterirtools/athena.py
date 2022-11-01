from datetime import date
from datetime import timedelta
import boto3
from IPython import display
import json
import os
import pyathena as pa
import pandas as pd
from pyathena.pandas.util import as_pandas
from pyathena import connect

from . import sso



session = sso.get_session("Jupyter-IR-AdministratorAccess", os.environ['MANAGEMENT_ACCOUNT'])
ssm_client = session.client('ssm')
    

database_response = ssm_client.get_parameter(Name='Jupyter-Athena-Database')
    
management_account = os.environ['MANAGEMENT_ACCOUNT']
management_region = 'us-east-1'
logging_account = os.environ['LOGGING_ACCOUNT']
database_name = database_response['Parameter']['Value']


def run_query(sql):
    sts_client = boto3.client('sts')

    response = sts_client.get_caller_identity()
    region_name = boto3.session.Session().region_name
    accountId = response['Account']

    s3_staging_dir="s3://aws-athena-query-results-{}-{}/".format(logging_account, management_region)

    profile_name = f"Jupyter-IR-ViewOnly-{logging_account}"
    
    print(f"profile_name={profile_name}")
    cursor = connect(s3_staging_dir=s3_staging_dir, region_name=management_region, profile_name=profile_name).cursor()

    sql = sql.replace('${database_name}', database_name)
    
    cursor.execute(sql)

    df = as_pandas(cursor)
    return df

def get_vpc_flow_by_account_eni(account_id, eni):
    today = date.today()
    yesterday = today - timedelta(days = 1)
    
    sql = f"""SELECT interface_id, srcaddr, srcport, dstaddr, dstport, count(packets) flow_count, sum(packets) packet_count, sum(bytes) sum_bytes
FROM "{database_name}"."vpc_flow_logs" 
WHERE "timestamp" >= '{str(yesterday.year).zfill(2)}/{str(yesterday.month).zfill(2)}/{str(yesterday.day).zfill(2)}'
AND accountid = '{account_id}' AND interface_id = '{eni}'
GROUP BY interface_id, srcaddr, srcport, dstaddr, dstport
ORDER BY count(packets) DESC
limit 100;"""

    return run_query(sql)

def get_vpc_flow_by_account(account_id):
    today = date.today()
    yesterday = today - timedelta(days = 1)
    
    sql = f"""SELECT interface_id, srcaddr, srcport, dstaddr, dstport, count(packets) flow_count, sum(packets) packet_count, sum(bytes) sum_bytes
FROM "{database_name}"."vpc_flow_logs" 
WHERE "timestamp" >= '{str(yesterday.year).zfill(2)}/{str(yesterday.month).zfill(2)}/{str(yesterday.day).zfill(2)}'
AND accountid = '{account_id}'
GROUP BY interface_id, srcaddr, srcport, dstaddr, dstport
ORDER BY count(packets) DESC
limit 100;"""

    return run_query(sql)