from datetime import date
from datetime import timedelta
from datetime import datetime 
import time
import boto3
import json
import os
import pandas as pd

QUERY_TIMEOUT = int( os.environ.get('QUERY_TIMEOUT', '120'))
CATALOG = os.environ.get('CATALOG', "AwsDataCatalog")

named_queries = None

def run_named_query(source, queryname, params=[]):
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
    
    return run_query_direct(named_query['QueryString'], named_query['Database'], params)

def run_query_direct(query_string, database, params = []):
    session = boto3.session.Session()
    athena_client = session.client('athena')
    sts_client = session.client('sts')
    account_id = sts_client.get_caller_identity()["Account"]
    
    s3_staging_dir="s3://aws-athena-query-results-{}-{}/".format(account_id, session.region_name)
    
    timeout_seconds = QUERY_TIMEOUT

    response = athena_client.start_query_execution(
        QueryString=query_string,
        QueryExecutionContext={
            "Database": database,
            "Catalog": CATALOG
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
    return df

