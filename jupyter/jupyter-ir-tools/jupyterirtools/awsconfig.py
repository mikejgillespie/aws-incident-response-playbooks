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

aggregator_response = ssm_client.get_parameter(Name='Jupyter-Config-Aggregator')

management_account = os.environ['MANAGEMENT_ACCOUNT']
management_region = 'us-east-1'
config_aggregator_id = aggregator_response['Parameter']['Value']



def run_query(query_expression, max_items = 200):
    profile = f"Jupyter-IR-AdministratorAccess-{management_account}"
    session = boto3.session.Session(profile_name=profile)
    config_client = session.client('config')

    paginator = config_client.get_paginator('select_aggregate_resource_config')
    
    page_iterator = paginator.paginate(
        Expression=query_expression,
        ConfigurationAggregatorName=config_aggregator_id,
        PaginationConfig={
            'MaxItems': max_items,
            'PageSize': 100
        }
    )
    
    jsonResults = []
    for page in page_iterator:
        for item in page['Results']:
            rec = {}
            json_item = json.loads(item)
            for field in page['QueryInfo']['SelectFields']:
                rec[field['Name']] = get_json_value(field['Name'], json_item)

            jsonResults.append(rec)

    df = pd.read_json(json.dumps(jsonResults))
    return df

def get_json_value(fieldName, obj):
    for field in fieldName.split('.'):
        if field in obj:
            obj = obj[field]
        else:
            obj = ''
    return obj
