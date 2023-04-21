from datetime import date
from datetime import timedelta
from datetime import datetime 
import time
import boto3
import json
import os
import pandas as pd

def get_default_staging_dir():
    session = boto3.session.Session()
    sts_client = session.client('sts')
    account_id = sts_client.get_caller_identity()["Account"]
    
    return "s3://aws-athena-query-results-{}-{}/".format(account_id, session.region_name)

S3_STAGING_DIR = os.environ.get('S3_STAGING_DIR', get_default_staging_dir())
QUERY_TIMEOUT = int( os.environ.get('QUERY_TIMEOUT', '120'))
CATALOG = os.environ.get('CATALOG', "AwsDataCatalog")
named_queries = None 

def run_named_query_with_sql(source, queryname, params={}):
    global named_queries
    session = boto3.session.Session()
    
    athena_client = session.client('athena')
        
    if named_queries is None:
        paginator = athena_client.get_paginator('list_named_queries')

        named_queries = {}

        for page in paginator.paginate(PaginationConfig={'PageSize': 50, 'MaxItems': 200}):
            
            response = athena_client.batch_get_named_query(
                NamedQueryIds=page['NamedQueryIds']
            )

            for named_query in response['NamedQueries']:
                named_queries[named_query['Name']] = named_query   
        
    named_query = named_queries[f"{queryname}_{source}"]
    
    return run_query(named_query['QueryString'], named_query['Database'], named_query['WorkGroup'], params)

def run_named_query(source, queryname, params={}):
    df, sql = run_named_query_with_sql(source,queryname, params)
    return df

def run_query(query_string, database="", workgroup="", params={}):
    session = boto3.session.Session()
    athena_client = session.client('athena')
    
    if not "region" in params:
        params["region"] = session.region_name
        
    if not "accountid" in params:
        sts_client = session.client('sts')
        params["accountid"] = sts_client.get_caller_identity()["Account"]
        
    sql = query_string.format(**params)
    
    timeout_seconds = QUERY_TIMEOUT

    start_execution_params = {
        "QueryString": sql,
        "ResultConfiguration":{
            'OutputLocation': S3_STAGING_DIR,
            'AclConfiguration': {
                'S3AclOption': 'BUCKET_OWNER_FULL_CONTROL'
            }
        }
    }
    
    if database != "":
        if not "QueryExecutionContext" in start_execution_params:
            start_execution_params["QueryExecutionContext"] = {}

        start_execution_params["QueryExecutionContext"]["Database"] = database

    if CATALOG != "":
        if not "QueryExecutionContext" in start_execution_params:
            start_execution_params["QueryExecutionContext"] = {}

        start_execution_params["QueryExecutionContext"]["Catalog"] = CATALOG
    
    if workgroup != "":
        start_execution_params["WorkGroup"] = workgroup
    
    
    response = athena_client.start_query_execution(**start_execution_params)
    query_execution_id = response['QueryExecutionId']
    
    timeout = datetime.now() + timedelta(seconds = timeout_seconds)

    response = athena_client.get_query_execution(
        QueryExecutionId=query_execution_id
    )

    status = response.get('QueryExecution', {}).get('Status', {}).get('State', "FAILED") 

    while datetime.now() < timeout and (status == "RUNNING" or status == "QUEUED"):
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
    return [df, sql]
