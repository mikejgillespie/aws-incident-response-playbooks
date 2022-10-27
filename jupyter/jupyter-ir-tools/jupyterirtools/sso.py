import os
import boto3
import subprocess
import shlex
from os.path import exists
from IPython.display import display,Javascript

def login(permission_set, account_id=''):
    
    if account_id=="":
        account_id = os.environ.get('LOGGING_ACCOUNT')
    
    init_profiles(permission_set, account_id)
    os.environ["AWS_PROFILE"] = f"{permission_set}-{account_id}"
    run_command("aws sso login --no-browser")

def get_management_session(permission_set):
    account_id = os.environ.get('MANAGEMENT_ACCOUNT')
    return get_session(permission_set, account_id)

def get_session(permission_set, account_id, region_name='us-east-1'):
    profile = f"{permission_set}-{account_id}"
    
    init_profiles(permission_set, account_id)

    return boto3.session.Session(profile_name=profile, region_name=region_name)
    
    
def run_command(command):
    process = subprocess.Popen(shlex.split(command), stdout=subprocess.PIPE)
    state = "initialize" 
    link = ""
    while True:
        output = process.stdout.readline()
        rc = process.poll()
        if rc is not None:
            break
        if output:
            txt_output = output.strip().decode('utf-8')
            if state == "await_code" and txt_output != "":
                state = "await_login" 
                link = f"{link}?user_code={txt_output}"
                print(f"If the windows doesn't automatically open, click on this {link} to activate the session")
                display(Javascript(f"window.open('{link}')"))
            elif state == "initialize" and txt_output.startswith("https"):
                link = f"{txt_output}"
            elif state == "initialize" and txt_output.startswith("Then enter the code:"):
                state = "await_code"
            #else:    
                #print(f"{txt_output}")
    rc = process.poll()
    return rc

def init_profiles(permission_set, account_id):

    if os.path.isfile(os.path.expanduser('~') + "/.aws/config"):
        with open(os.path.expanduser('~') + "/.aws/config") as myfile:
            if f'{permission_set}-{account_id}' in myfile.read():
                #print("Profile found")
                return
    
    
    profile_name = f"{permission_set}-{account_id}"
    cr = '\n'
    aws_config = f"[profile {profile_name}]{cr}"
    aws_config += f"sso_start_url = {os.environ['SSO_URL']}{cr}"
    aws_config += f"sso_region ={os.environ['SSO_REGION']}{cr}"
    aws_config += f"sso_account_id = {account_id}{cr}"
    aws_config += f"sso_role_name = {permission_set}{cr}"
    aws_config += f"region = {os.environ['SSO_REGION']}{cr}"
    aws_config += '\n'

    f = open(os.path.expanduser('~') + "/.aws/config", "a")
    f.write(aws_config)
    f.close()
    #print(aws_config)