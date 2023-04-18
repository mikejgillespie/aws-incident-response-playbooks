from datetime import date
import time
from datetime import timedelta
import datetime
import boto3
from IPython import display
import json
import os
import pyathena as pa
import pandas as pd
from pyathena.pandas.util import as_pandas
from pyathena import connect
import datetime 
import time
    
from . import sso



session = sso.get_session("Jupyter-IR-AdministratorAccess", os.environ['LOGGING_ACCOUNT'])
ssm_client = session.client('ssm')
    

database_response = ssm_client.get_parameter(Name='Jupyter-Athena-Glue-Database')
cloudtrail_response = ssm_client.get_parameter(Name='Jupyter-Athena-CloudTrail-Table')
flowlogs_response = ssm_client.get_parameter(Name='Jupyter-Athena-FlowLogs-Table')
    
management_account = os.environ['MANAGEMENT_ACCOUNT']
management_region = 'us-east-1'
logging_account = "913149361159" #os.environ['LOGGING_ACCOUNT']
cloudtrail_table = cloudtrail_response['Parameter']['Value']
flowlogs_table = flowlogs_response['Parameter']['Value']
database_name = database_response['Parameter']['Value']



def run_named_query(source, queryname, params=[]):
    athena_client = boto3.client('athena')

    response1 = athena_client.list_named_queries()#NamedQueryId="cloudtrail_security_lake")

    response = athena_client.batch_get_named_query(
        NamedQueryIds=response1['NamedQueryIds']
    )

    named_queries = {}
    for named_query in response['NamedQueries']:
        named_queries[named_query['Name']] = named_query   
        
    sql = named_queries[f"{queryname}_{source}"]['QueryString']
    
    s3_staging_dir="s3://aws-athena-query-results-{}-{}/".format(logging_account, management_region)

    
    response = athena_client.start_query_execution(
        QueryString=sql,
        QueryExecutionContext={
            "Database": "amazon_security_lake_glue_db_us_east_1",
            "Catalog": "AwsDataCatalog"
        },
        ResultConfiguration={
            'OutputLocation': s3_staging_dir,
            'AclConfiguration': {
                'S3AclOption': 'BUCKET_OWNER_FULL_CONTROL'
            }
        },
        ExecutionParameters=params
    )
    query_execution_id = response['QueryExecutionId']
    return run_query_direct(query_execution_id, params)

def run_query_direct(query_execution_id, params = []):
    timeout_seconds = 15

    timeout = datetime.datetime.now() + datetime.timedelta(seconds = timeout_seconds)


    athena_client = boto3.client('athena')

    response = athena_client.get_query_execution(
        QueryExecutionId=query_execution_id
    )

    status = response.get('QueryExecution', {}).get('Status', {}).get('State', "FAILED") 

    while datetime.datetime.now() < timeout and (status == "RUNNING" or status == "QUEUED"):
        time.sleep(1)
        response = athena_client.get_query_execution(
            QueryExecutionId=query_execution_id
        )
        status = response.get('QueryExecution', {}).get('Status', {}).get('State', "FAILED") 

    results = []
    if status == "SUCCEEDED":
        paginator = athena_client.get_paginator('get_query_results')
        for page in paginator.paginate(QueryExecutionId=query_execution_id):
            rowNbr = 1
            while rowNbr < len(page['ResultSet']['Rows']):
                row = page['ResultSet']['Rows'][rowNbr]
                rowNbr+=1
                i=0
                item = {}
                while i < len(page['ResultSet']['ResultSetMetadata']['ColumnInfo']):
                    column = page['ResultSet']['ResultSetMetadata']['ColumnInfo'][i]
                    item[column['Name']] = row['Data'][i].get('VarCharValue', '')
                    i += 1
                results.append(item)


    df = pd.DataFrame.from_dict(results)
    return df

def run_query(sql, params=[]):
    sts_client = boto3.client('sts')

    response = sts_client.get_caller_identity()
    region_name = boto3.session.Session().region_name
    accountId = response['Account']

    s3_staging_dir="s3://aws-athena-query-results-{}-{}/".format(logging_account, management_region)

    profile_name = f"Jupyter-IR-AdministratorAccess-{logging_account}"
    
    print(f"profile_name={profile_name}")
    cursor = connect(s3_staging_dir=s3_staging_dir, region_name=management_region, profile_name=profile_name).cursor()

    sql = sql.replace('${database_name}', database_name)
    sql = sql.replace('${cloudtrail_table}', cloudtrail_table)
    
    cursor.execute(sql)

    df = as_pandas(cursor)
    return df

def get_vpc_flow_by_account_eni(account_id, eni):
    today = date.today()
    yesterday = today - timedelta(days = 1)
    
    sql = f"""SELECT interface_id, srcaddr, srcport, dstaddr, dstport, count(packets) flow_count, sum(packets) packet_count, sum(bytes) sum_bytes
FROM "{database_name}"."{flowlogs_table}" 
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
FROM "{database_name}"."{flowlogs_table}" 
WHERE "timestamp" >= '{str(yesterday.year).zfill(2)}/{str(yesterday.month).zfill(2)}/{str(yesterday.day).zfill(2)}'
AND accountid = '{account_id}'
GROUP BY interface_id, srcaddr, srcport, dstaddr, dstport
ORDER BY count(packets) DESC
limit 100;"""

    return run_query(sql)

def get_vpc_flow_by_account_region(account_id, region_name):
    session = sso.get_session("Jupyter-IR-AdministratorAccess", account_id, region_name)
    client = session.client('ec2')
    response = client.describe_flow_logs()
    today = datetime.datetime.now()
    yesterday = today - timedelta(days = 1)

    flow_log_ids = []
    for flow_log in response['FlowLogs']:
        flow_log_id = flow_log['FlowLogId']
        options = "cloudwatch"
        
        if "DestinationOptions" in flow_log:
            options = flow_log['DestinationOptions']['FileFormat']
        
        if options == "cloudwatch":
            log_group_name = flow_log['LogGroupName']
            return get_from_cloudwatch(account_id, region_name, log_group_name)
        else:
            return get_from_athena(account_id, region_name)
            
def get_from_athena(account_id, region_name):
    
    today = date.today()
    yesterday = today - timedelta(days = 1)
    
    sql = f"""SELECT interface_id, srcaddr, srcport, dstaddr, dstport, count(packets) flow_count, sum(packets) packet_count, sum(bytes) sum_bytes
FROM "{database_name}"."{flowlogs_table}" 
WHERE "timestamp" >= '{str(yesterday.year).zfill(2)}/{str(yesterday.month).zfill(2)}/{str(yesterday.day).zfill(2)}'
AND accountid = '{account_id}'
AND region = '{region_name}'
GROUP BY interface_id, srcaddr, srcport, dstaddr, dstport
ORDER BY count(packets) DESC
limit 100;"""

    return run_query(sql)

def get_from_cloudwatch(account_id, region_name, log_group_name):
    session = sso.get_session("Jupyter-IR-AdministratorAccess", account_id, region_name)
    
    cloudwatch_client = session.client('logs')
            
    t = int(time.time())
    y = t - 1440

    query = """
fields accountId, action, logStatus, interfaceId, bytes, packets, protocol, srcAddr, dstAddr, srcPort, dstPort, start, end, version
"""

    start_query_response = cloudwatch_client.start_query(
                logGroupName=log_group_name,
                startTime=y,
                endTime=t,
                queryString=query
            )
            
    query_id = start_query_response['queryId']

    response = None
            


    while response == None or response['status'] == 'Running':
        print('Waiting for query to complete ...')
        time.sleep(1)
        response = cloudwatch_client.get_query_results(
            queryId=query_id
        )
            
    recs =[]
            
          
    for row in response['results']:
        rec = {}
        for field in response['results'][0]:
            if field['field'] != '@ptr':
                rec[field['field']] = field['value']
        recs.append(rec)

    dataframe = pd.DataFrame.from_dict(recs, orient="columns")
    return dataframe