import os
import boto3
import subprocess
import shlex
from os.path import exists
from IPython.display import display,Javascript, Markdown
import json
from configparser import ConfigParser
from datetime import datetime, timedelta, timezone
from pathlib import Path
import dateutil, time, binascii, hashlib, math
from botocore import UNSIGNED
from botocore.config import Config

AWS_CONFIG_PATH = f"{Path.home()}/.aws/config"
AWS_CREDENTIAL_PATH = f"{Path.home()}/.aws/credentials"
AWS_SSO_CACHE_PATH = f"{Path.home()}/.aws/sso/cache"

sso_start_url = os.environ['SSO_URL']
aws_region = os.environ['SSO_REGION']
    
def login(permission_set = '', account_id='', force_login = False):
    
    if account_id=="":
        account_id = os.environ.get('LOGGING_ACCOUNT')
    
    sso_login(force_login)
    
    if permission_set != '':
        os.environ["AWS_PROFILE"] = f"{permission_set}-{account_id}"
        init_profiles(permission_set, account_id)
    

def get_management_session(permission_set):
    account_id = os.environ.get('MANAGEMENT_ACCOUNT')
    return get_session(permission_set, account_id)

def get_session(permission_set, account_id='', region_name='us-east-1'):
    if account_id=="":
        account_id = os.environ.get('LOGGING_ACCOUNT')
        
    profile = f"{permission_set}-{account_id}"
    
    init_profiles(permission_set, account_id)

    return boto3.session.Session(profile_name=profile, region_name=region_name)
    

def init_profiles(permission_set, account_id):
    config = read_config(AWS_CONFIG_PATH)
    
    profile_name = f"profile {permission_set}-{account_id}"
    if config.has_section(profile_name):
        config.remove_section(profile_name)
    config.add_section(profile_name)
    config.set(profile_name, "sso_start_url", f"{sso_start_url}")
    config.set(profile_name, "sso_region ", f"{aws_region}")
    config.set(profile_name, "sso_account_id", f"{account_id}")
    config.set(profile_name, "sso_role_name", f"{permission_set}")
    config.set(profile_name, "region", f"{aws_region}")
            
    write_config(AWS_CONFIG_PATH, config)
    
def get_sso_cached_login():
    file_paths = list_directory(AWS_SSO_CACHE_PATH)
    for file_path in file_paths:
        data = load_json(file_path)
        if not (data.get("startUrl") and data.get("startUrl").startswith(sso_start_url)) or\
                data.get("region") != aws_region or iso_time_now() > parse_timestamp(data["expiresAt"]):
            continue
        client_config = Config(signature_version=UNSIGNED, region_name='us-east-1')
        sso = boto3.client("sso", config=client_config)
        
        try:
            accounts = sso.list_accounts(accessToken=data['accessToken'], maxResults=1)
        except sso.exceptions.UnauthorizedException:
            raise ExpiredSSOCredentialsError("Current cached SSO login is expired or invalid")

        diff = parse_timestamp(data["expiresAt"]) - iso_time_now()
        minutes = int(diff.total_seconds() / 60)
        hours = math.floor(minutes/60)
        minutes = minutes % 60
        
        print(f'Credentials expire in {hours} hours and {minutes} minutes')
        
        
        return data['accessToken']
    raise ExpiredSSOCredentialsError("Current cached SSO login is expired or invalid")


def iso_time_now():
    return datetime.now(timezone.utc)


def list_directory(path):
    file_paths = []
    if os.path.exists(path):
        file_paths = Path(path).iterdir()
    file_paths = sorted(file_paths, key=os.path.getmtime)
    file_paths.reverse()  # sort by recently updated
    return [str(f) for f in file_paths]


def load_json(path):
    try:
        with open(path) as context:
            return json.load(context)
    except ValueError:
        pass  # ignore invalid json


def parse_timestamp(value):
    return dateutil.parser.parse(value)


def read_config(path):
    config = ConfigParser()
    config.read(path)
    return config


def write_config(path, config):
    with open(path, "w") as destination:
        config.write(destination)


def role_name(role_data):
    return role_data['roleName']


def update_aws_credentials(new_credentials):
    config = read_config(AWS_CONFIG_PATH)
    print("Updating credentials")
    for profile_credential in new_credentials:
        profile_name = profile_credential['accountName']
        if config.has_section(profile_name):
            config.remove_section(profile_name)
        config.add_section(profile_name)
        config.set(profile_name, "aws_access_key_id", profile_credential["accessKeyId"])
        config.set(profile_name, "aws_secret_access_key ", profile_credential["secretAccessKey"])
        config.set(profile_name, "aws_session_token", profile_credential["sessionToken"])
    write_config(AWS_CONFIG_PATH, config)


class ExpiredSSOCredentialsError(Exception):
    pass


def fetch_access_token():

    try:
        return get_sso_cached_login()
    except ExpiredSSOCredentialsError as error:
        print(error)
        print("Fetching credentials again")
        return renew_access_token()


def renew_access_token():
    client = boto3.client('sso-oidc', region_name = aws_region)
    client_name = 'aws-sso-script'
    client_hash = hashlib.sha1(sso_start_url.encode('utf-8'))

    client_hash_filename = f"{binascii.hexlify(client_hash.digest()).decode('ascii')}.json"
    
    register_client_response = client.register_client(clientName=client_name, clientType='public')
    client_id = register_client_response['clientId']
    client_secret = register_client_response['clientSecret']
    start_authorization_response = client.start_device_authorization(clientId=client_id, clientSecret=client_secret,
                                                                     startUrl=sso_start_url)
    device_code = start_authorization_response['deviceCode']
    verification_uri = start_authorization_response['verificationUriComplete']
    
    display(Markdown(f"If the login window doesn't automatically open, click to [activate the session]({verification_uri})"))
    display(Javascript(f"window.open('{verification_uri}')"))
    
    login_waiting = True
    create_token_response = {}
    access_token = ""
    cnt = 0
    #set a timeout
    while login_waiting:
        if cnt % 10 == 0:
            print("Waiting for login...")
        time.sleep(1)
        try:
            create_token_response = client.create_token(
                clientId=client_id,
                clientSecret=client_secret,
                grantType='urn:ietf:params:oauth:grant-type:device_code',
                deviceCode=device_code,
                code=device_code
            )
            expiration_date = iso_time_now() + timedelta(0, create_token_response['expiresIn'])
            expiration_date_iso = expiration_date.isoformat()
            access_token = create_token_response['accessToken']
            login_waiting = False
            
            diff = parse_timestamp(expiration_date_iso) - iso_time_now()
            minutes = int(diff.total_seconds() / 60)
            hours = math.floor(minutes/60)
            minutes = minutes % 60
        
            print(f'Credentials expire in {hours} hours and {minutes} minutes')
            
            with open(f'{AWS_SSO_CACHE_PATH}/{client_hash_filename}', 'w') as cache_file:
                cache_file.write(json.dumps({
                    'accessToken': access_token,
                    'expiresAt': expiration_date_iso,
                    'region': aws_region,
                    'startUrl': sso_start_url
                }))
        except client.exceptions.AuthorizationPendingException as err:
            cnt += 1
        except Exception as err:
            print(f"Unexpected {err}, {type(err)}")

    print("Login Successful")
    return access_token

def fetch_accouts_credentials():
    return ""

def logout():
    
    file_paths = list_directory(AWS_SSO_CACHE_PATH)
    for file_path in file_paths:
        data = load_json(file_path)
        if not (data.get("startUrl") and data.get("startUrl").startswith(sso_start_url)) or\
                data.get("region") != aws_region or iso_time_now() > parse_timestamp(data["expiresAt"]):
            continue
        client_config = Config(signature_version=UNSIGNED, region_name='us-east-1')
        sso = boto3.client("sso", config=client_config)
        
        try:
            sso.logout(accessToken=data['accessToken'])
        except sso.exceptions.UnauthorizedException:
            # This is ok, we're logging out.
            pass
    

def print_permissions():
    access_token = ""
    
    file_paths = list_directory(AWS_SSO_CACHE_PATH)
    for file_path in file_paths:
        data = load_json(file_path)
        if not (data.get("startUrl") and data.get("startUrl").startswith(sso_start_url)) or\
                data.get("region") != aws_region or iso_time_now() > parse_timestamp(data["expiresAt"]):
            continue
        client_config = Config(signature_version=UNSIGNED, region_name='us-east-1')
        sso = boto3.client("sso", config=client_config)
        
        access_token = data['accessToken']


    if access_token == "":
        print("No Access Token, please log in")
        return;
    
    client_config = Config(signature_version=UNSIGNED, region_name='us-east-1')
    sso = boto3.client("sso", config=client_config)
    paginator = sso.get_paginator('list_accounts')
    results = paginator.paginate(accessToken=access_token)
    account_list = results.build_full_result()['accountList']
    for account in account_list:
        sso_account_id = account['accountId']
        sso_account_name = account['accountName'].replace("_", "-")
        paginator = sso.get_paginator('list_account_roles')
        results = paginator.paginate(
            accountId=sso_account_id,
            accessToken=access_token
        )
        role_list = results.build_full_result()['roleList']
        role_list.sort(key=role_name)
        
        for role in role_list:
            print(f"Account: {role['accountId']}: Role: {role['roleName']}")
        
'''
- You need botocore and boto3 with python3
- Exec this with python path/to/this/file.py
- I'll get default values for sso_region and sso_start_url from your ~/.aws/config file, you can overwrite it anyways when you run the script
- It updates ~/.aws/credentials will all credentials assigned in your SSO account
'''
def sso_login(force_login = False):
    
    if force_login:
        logout()
        
    access_token = fetch_access_token()

    return access_token