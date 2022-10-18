from datetime import date
from datetime import timedelta
import boto3
from IPython import display
import json
import pyathena as pa
import pandas as pd
from pyathena.pandas.util import as_pandas
from pyathena import connect

session = boto3.Session(profile_name='default')
ssm_client = session.client('ssm')
    
management_account_response = ssm_client.get_parameter(Name='Jupyter-Management-Account')
management_region_response = ssm_client.get_parameter(Name='Jupyter-Management-Region')
logging_account_response = ssm_client.get_parameter(Name='Jupyter-Athena-LoggingAccount')
database_response = ssm_client.get_parameter(Name='Jupyter-Athena-Database')
    
management_account = management_account_response['Parameter']['Value']
management_region = management_region_response['Parameter']['Value']
logging_account = logging_account_response['Parameter']['Value']
database_name = database_response['Parameter']['Value']


def run_query(sql):

    
    #print(query)
    sts_client = boto3.client('sts')

    response = sts_client.get_caller_identity()
    region_name = boto3.session.Session().region_name
    accountId = response['Account']

    s3_staging_dir="s3://aws-athena-query-results-{}-{}/".format(logging_account, management_region)

    profile_name = f"Jupyter-IR-ViewOnly-{logging_account}"
    
    print(f"profile_name={profile_name}")
    cursor = connect(s3_staging_dir=s3_staging_dir, region_name=management_region, profile_name=profile_name).cursor()

    cursor.execute(sql)

    df = as_pandas(cursor)
    return df

def get_vpc_flow_by_eni(eni_id):
    today = date.today()
    yesterday = today - timedelta(days = 1)
    
    sql = f"""SELECT interface_id, srcaddr, srcport, dstaddr, dstport, count(packets) flow_count, sum(packets) packet_count, sum(bytes) sum_bytes
FROM "{database_name}"."vpc_flow_logs" 
WHERE ((year = '{str(today.year)}'
AND month ='{str(today.month).zfill(2)}'
AND day >= '{str(today.day).zfill(2)}') OR (
year = '{str(yesterday.year)}'
AND month ='{str(yesterday.month).zfill(2)}'
AND day >= '{str(yesterday.day).zfill(2)}'))
AND interface_id = '{eni_id}'
GROUP BY interface_id, srcaddr, srcport, dstaddr, dstport
ORDER BY count(packets) DESC
limit 100;"""
    return run_query(sql)