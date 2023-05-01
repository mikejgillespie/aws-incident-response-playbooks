import os
import boto3
import botocore.exceptions
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
from pathlib import Path
import urllib, sys
import requests # 'pip install requests'
from . import utils


# Set global variables for the default location of the AWS config files
AWS_CONFIG_PATH = f"{Path.home()}/.aws/config"
AWS_CREDENTIAL_PATH = f"{Path.home()}/.aws/credentials"
AWS_SSO_CACHE_PATH = f"{Path.home()}/.aws/sso/cache"

# The environment needs to supply the AWS SSO Url and the AWS SSO region in order to connect to SSO.
sso_start_url = os.environ.get('SSO_URL', '')
aws_region = os.environ.get('SSO_REGION', '')


linked_roles_str = os.environ.get('LINKED_ROLES', '')
linked_roles = linked_roles_str.split(',') if linked_roles_str != "" else []
default_role = os.environ.get('DEFAULT_ROLE', ''  if len(linked_roles)==0 else linked_roles[0])

auth_type = "DEFAULT"
if sso_start_url != "":
    auth_type = "SSO"
elif len(linked_roles) > 0:
    auth_type = "ASSUME_ROLE"

#auth_type = "ASSUME_ROLE"
#auth_type = "DEFAULT"
#default_account = "383086473915"
#default_role = "Jupyter-IR-ViewOnly"

def parse_role_arn(arn):
    arn_info = arn.split(':')
    role_name = arn_info[5][5:]
    return [arn_info[4], role_name ]

def login(force_login = False):
    global default_role
    
    """
    login does creates an SSO session for the current user. If a session already exists, it will
    be reused. If supplied, the given permission set and account ID will be used to set the
    default profile in the AWSfprint CLI and Boto2 SDK.

    :param permission_set: The permission set to use for the default boto3 session
    :param account_id: The AWS account ID set to use for the default boto3 session
    :param force_login: If true, invalidates the current SSO session and begins a new one.
    """    
    
    if auth_type == "SSO":
        print('Logging in with IAM Identity Center....')
        
        sso_login(force_login)  
        
        if default_role == '' and len(linked_roles) > 0:
            default_role = linked_roles[0]
            
        account_id, permission_set = parse_role_arn(default_role)
        init_profiles(permission_set, account_id)
        os.environ["AWS_PROFILE"] = f"{permission_set}-{account_id}"
        

    elif auth_type == "ASSUME_ROLE":
        
        if default_role == '' and len(linked_roles) > 0:
            default_role = linked_roles[0]
        
        account_id, role_name = parse_role_arn(default_role)
        
        print(f'Use role assumption: Default {default_role}')
        
        my_session = boto3.session.Session()
        my_region = my_session.region_name
        init_profiles_assume_role(role_name, account_id, my_region)
        os.environ["AWS_PROFILE"] = f"{role_name}-{account_id}"
        
    else:
        print('Using default profile')
        sts = boto3.client('sts')
        identity = sts.get_caller_identity()
        arn_info = identity['Arn'].split(':')
        account_id = arn_info[4]
        principal_info = arn_info[5].split('/')
        principal_type = principal_info[0]
        principal_name = principal_info[1]
        rolesession_name = ""
        
        if principal_type == 'assumed-role':
            rolesession_name = principal_info[2]
        
        print(f"Account: {account_id}, principal: {principal_name} {'role session: ' + rolesession_name if rolesession_name != ''  else ''}")
        
def get_client_by_account_region(role, service, accounts=[], regions=['us-east-1']):
    result = []
    
    for account in accounts:
        for region in regions:    
            session = get_session(role,account)
            
            result.append([
                session.client(service, region_name=region),
                account,
                region
            ])
    
    return result

def get_session_by_account(role=''):
    result = []
    if auth_type=="DEFAULT":
        sts = boto3.client('sts')
        identity = sts.get_caller_identity()
        arn_info = identity['Arn'].split(':')
        account_id = arn_info[4]
        principal_info = arn_info[5].split('/')
        principal_type = principal_info[0]
        principal_name = principal_info[1]
        
        session = get_session(principal_name,account_id)
        result.append([session, account_id])
    else:
        for role_arn in linked_roles:
            account, assumed_role = parse_role_arn(role_arn)
            
            if role == "" or assumed_role == role:
                session = get_session(assumed_role,account)
                result.append([session, account])
    return result

# get_sess
def get_session(permission_set='', account_id='', region_name='us-east-1'):
    """
    get_session creates a boto3 session for the permission set, account id, and region. 
    Prior to creating the session, the profile will be configured in the ~/.aws/config file. 
    This eliminates the need to call aws sso configure for every account and permission set 
    variation.

    :param permission_set: The permission set to use for the new boto3 session
    :param account_id: The AWS account ID set to use for the new boto3 session
    :param region_name: The region name for the new AWS boto3 session.
    """    
    
    if auth_type=="DEFAULT":
        return boto3.session.Session();
    
    if permission_set == '' and account_id == '':
        account_id, permission_set = parse_role_arn(default_role)
        
    profile = f"{permission_set}-{account_id}"
    
    init_profiles(permission_set, account_id)

    return boto3.session.Session(profile_name=profile, region_name=region_name)
        
def init_profiles_sso(permission_set, account_id):
    """
    init_profiles populates the ~/.aws/config file with the profile for the given
    permission set and account ID. It will either create the profile as an SSO profile
    or through the JUMP_ACCOUNT system variable..

    :param permission_set: The permission set to use for the new boto3 profile
    :param account_id: The AWS account ID set to use for the new boto3 profile
    organization
    """  
    
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
    return profile_name

def init_profiles(permission_set, account_id):
    if auth_type == "SSO":
        return init_profiles_sso(permission_set, account_id);
    elif auth_type == "ASSUME_ROLE":
        return init_profiles_assume_role(permission_set, account_id);
    
def init_profiles_assume_role(permission_set, account_id, region=''):
    """
    init_profiles populates the ~/.aws/config file with the profile for the given
    permission set and account ID. It will either create the profile as an SSO profile
    or through the JUMP_ACCOUNT system variable..

    :param permission_set: The permission set to use for the new boto3 profile
    :param account_id: The AWS account ID set to use for the new boto3 profile
    :param external_account: True if this account external to AWS organizations, otherise it is part of the AWS
    organization
    """  
    
    config = read_config(AWS_CONFIG_PATH)
    
    region = 'us-east-1' if region == '' else region
    
    profile_name = f"profile {permission_set}-{account_id}"
    if config.has_section(profile_name):
        config.remove_section(profile_name)
        
    config.add_section(profile_name)
        
    config.set(profile_name, "role_arn", f"arn:aws:iam::{account_id}:role/{permission_set}")
    config.set(profile_name, "credential_source", "Ec2InstanceMetadata")
    config.set(profile_name, "role_session_name ", f"jupyter")
    config.set(profile_name, "region", f"{region}")
            
    write_config(AWS_CONFIG_PATH, config)
    return profile_name
    
def get_sso_cached_login():
    """
    get_sso_cached_login attempts to load the active SSO session based on the AWS_SSO_CACHE_PATH.
    If the cached sso data is valid, it will return that SSO session, otherise it will raise an ExpiredSSOCredentialsError error.

    :param permission_set: The permission set to use for the new boto3 profile
    :param account_id: The AWS account ID set to use for the new boto3 profile
    :param external_account: True if this account external to AWS organizations, otherise it is part of the AWS
    organization
    """  
    if not os.path.exists(AWS_SSO_CACHE_PATH):
        raise ExpiredSSOCredentialsError("Current cached SSO login is expired or invalid")
        
    file_paths = list_directory(AWS_SSO_CACHE_PATH)
    for file_path in file_paths:
        data = load_json(file_path)
        if not (data.get("startUrl") and data.get("startUrl").startswith(sso_start_url)) or\
                data.get("region") != aws_region or iso_time_now() > parse_timestamp(data["expiresAt"]):
            continue
        client_config = Config(signature_version=UNSIGNED, region_name='us-east-1')
        sso = boto3.client("sso", config=client_config)
        
        try:
            #print(f"accessToken: {data['accessToken']}")
            accounts = sso.list_accounts(accessToken=data['accessToken'], maxResults=1)
        except sso.exceptions.UnauthorizedException:
            raise ExpiredSSOCredentialsError("Current cached SSO login is expired or invalid")

        diff = parse_timestamp(data["expiresAt"]) - iso_time_now()
        minutes = int(diff.total_seconds() / 60)
        hours = math.floor(minutes/60)
        minutes = minutes % 60
        
        display(Markdown(f'Credentials expire in {hours} hours and {minutes} minutes'))
        
        
        return data['accessToken']
    raise ExpiredSSOCredentialsError("Current cached SSO login is expired or invalid")


def iso_time_now():
    """
    Returns the current UTC time

    :return: The current UTC time.
    """  
    return datetime.now(timezone.utc)


def list_directory(path):
    """
    list_directory returns a list of all the files in a folder.

    :param path: The path to list the files.
    :return: A list of strings with the full file name.
    organization
    """  
    file_paths = []
    if os.path.exists(path):
        file_paths = Path(path).iterdir()
    file_paths = sorted(file_paths, key=os.path.getmtime)
    file_paths.reverse()  # sort by recently updated
    return [str(f) for f in file_paths]


def load_json(path):
    try:
        with open(path, "r+") as context:
            return json.load(context)
    except ValueError:
        pass  # ignore invalid json


def parse_timestamp(value):
    return dateutil.parser.parse(value)


def read_config(path):
    # create file if it does not exist
    file = open(path, 'a+')
    file.close()
    
    config = ConfigParser()
    config.read(path)
    return config


def write_config(path, config):
    with open(path, "w+") as destination:
        config.write(destination)


def role_name(role_data):
    return role_data['roleName']

class ExpiredSSOCredentialsError(Exception):
    pass


def fetch_access_token():
    """
    fetch_access_token returns the access token for this current session.

    :return: The cached access token, otherwise, a new access token is generated.
    organization
    """ 
    try:
        return get_sso_cached_login()
    except ExpiredSSOCredentialsError as error:
        print(error)
        print("Fetching credentials again")
        return renew_access_token()


def renew_access_token():
    """
    renew_access_token uses the boto3 sso-oidc library to create a new SSO session

    :return: The access token of the validated SSO session.
    organization
    """  
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
        
            display(Markdown(f'Credentials expire in {hours} hours and {minutes} minutes'))
            
            Path(AWS_SSO_CACHE_PATH).mkdir(parents=True, exist_ok=True)
            
            with open(f'{AWS_SSO_CACHE_PATH}/{client_hash_filename}', 'w+') as cache_file:
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


def logout():
    """
    logout invalidates the current SSO session and all new requests will need to be reauthenticated.
    """     
    if auth_type != "SSO":
        return
    
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
    
def check_permissions():
    results = []
    if auth_type == "SSO" or auth_type == "ASSUME_ROLE":
        for role_arn in linked_roles:
            try:
                account, role = parse_role_arn(role_arn)
                session = get_session(role, account)
                sts = session.client('sts')
                identity = sts.get_caller_identity()
                
                results.append({"Account": account, "Role": role, "Status": "Successful"})

            except botocore.exceptions.ClientError as error:
                results.append({"Account": account, "Role": role, "Status": "Access Denied"})
                    
    else:
        sts = boto3.client('sts')
        identity = sts.get_caller_identity()
        arn_info = identity['Arn'].split(':')
        account_id = arn_info[4]
        principal_info = arn_info[5].split('/')
        principal_type = principal_info[0]
        principal_name = principal_info[1]
        results.append({"Account": account_id, "Role": principal_name, "Status": "Successful"})

    utils.display_results_status("Account Status", results, lambda x: 1 if x['Status'] == "Successful" else 3)




def get_permissions_sso():
    """
    print_permissions uses the boto3 sso library to list all the account & permission set access the current user has access to.
    """ 
    global linked_roles

    access_token = ""
    
    file_paths = list_directory(AWS_SSO_CACHE_PATH)
    for file_path in file_paths:
        data = load_json(file_path)
        if not (data.get("startUrl") and data.get("startUrl").startswith(sso_start_url)) or\
                data.get("region") != aws_region or iso_time_now() > parse_timestamp(data["expiresAt"]):
            continue
        
        #init_profiles("Jupyter-IR-ViewOnly", os.environ.get('MANAGEMENT_ACCOUNT'))
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
    linked_roles = []
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
            linked_roles.append(f"arn:aws:iam::{sso_account_id}:role/{role['roleName']}")
        

def sso_login(force_login = False):
    """
    get_sso_cached_login attempts to load the active SSO session based on the AWS_SSO_CACHE_PATH.
    If the cached sso data is valid, it will return that SSO session, otherise it will raise an ExpiredSSOCredentialsError error.

    :param force_login: Invalidate tokens to start to force a new login.
    :return: The current access token for the active SSO session.
    """     
    
    if force_login:
        logout()
    
    access_token = fetch_access_token()
    
    
    #write_console_link(account_id, role_name, access_token)
    get_permissions_sso()


def write_console_link(account_id, role_name, access_token):
    link_url = get_link_url(account_id, role_name, access_token, "https://console.aws.amazon.com/" )
    display(Markdown(f"Login Successful, click to open [AWS Console]({link_url})"))
    
    
def get_link_url(account_id, role_name, access_token, destination_url):
    sso_client = boto3.client('sso')
    
 
    response = sso_client.get_role_credentials(
        roleName=role_name,
        accountId=account_id,
        accessToken=access_token
    )
    # Step 1: Enter the session credentials

    access_key_id = response['roleCredentials']['accessKeyId']
    secret_access_key = response['roleCredentials']['secretAccessKey']
    session_token = response['roleCredentials']['sessionToken']

    # Step 2: Format resulting temporary credentials into JSON
    url_credentials = {}
    url_credentials['sessionId'] = access_key_id
    url_credentials['sessionKey'] = secret_access_key
    url_credentials['sessionToken'] = session_token
    json_string_with_temp_credentials = json.dumps(url_credentials)

    # Step 3. Make request to AWS federation endpoint to get sign-in token. Construct the parameter string with
    # the sign-in action request, a 12-hour session duration, and the JSON document with temporary credentials 
    # as parameters.
    request_parameters = "?Action=getSigninToken"
    request_parameters += "&SessionDuration=43200"
    if sys.version_info[0] < 3:
        def quote_plus_function(s):
            return urllib.quote_plus(s)
    else:
        def quote_plus_function(s):
            return urllib.parse.quote_plus(s)
    request_parameters += "&Session=" + quote_plus_function(json_string_with_temp_credentials)
    request_url = "https://signin.aws.amazon.com/federation" + request_parameters
    r = requests.get(request_url)
    # Returns a JSON document with a single element named SigninToken.
    signin_token = json.loads(r.text)

    # Step 4: Create URL where users can use the sign-in token to sign in to 
    # the console. This URL must be used within 15 minutes after the
    # sign-in token was issued.
    request_parameters = "?Action=login" 
    request_parameters += "&Issuer=Example.org" 
    request_parameters += "&Destination=" + quote_plus_function("https://console.aws.amazon.com/")
    request_parameters += "&SigninToken=" + signin_token["SigninToken"]
    request_url = "https://signin.aws.amazon.com/federation" + request_parameters

    return request_url


login() # automatically login