import os
import boto3
import subprocess
import shlex
from os.path import exists
from IPython.display import display,Javascript

def login(permission_set, account_id):
    init_profiles(permission_set, account_id)
    os.environ["AWS_PROFILE"] = f"{permission_set}-{account_id}"
    run_command("/usr/local/bin/aws sso login --no-browser")
    
    
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
    session = boto3.Session(profile_name='default')
    ssm_client = session.client('ssm')

    sso_portal_url_response = ssm_client.get_parameter(Name='Jupyter-SSO-Portal-Url')
    sso_instance_response = ssm_client.get_parameter(Name='Jupyter-SSO-Directory')
    sso_instance_arn_response = ssm_client.get_parameter(Name='Jupyter-SSO-Instance-Arn')


    sso_portal_url = sso_portal_url_response['Parameter']['Value']
    sso_identity_store_id = sso_instance_response['Parameter']['Value']
    sso_identity_store_arn = sso_instance_arn_response['Parameter']['Value']
    
    sso_region = "us-east-1"

    session = boto3.Session(profile_name='default')
    sso_admin_client = session.client('sso-admin', region_name = sso_region)
    
    if os.path.isfile(os.path.expanduser('~') + "/.aws/config"):
        with open(os.path.expanduser('~') + "/.aws/config") as myfile:
            if f'{permission_set}-{account_id}' in myfile.read():
                print("Profile found")
                return
            else:
                os.rename(os.path.expanduser('~') + "/.aws/config", os.path.expanduser('~') + "/.aws/config.bak")    
    
    aws_config = f"""[default]
region = {sso_region}
"""

    permission_sets = sso_admin_client.list_permission_sets(InstanceArn=sso_identity_store_arn)

    for permission_set in permission_sets['PermissionSets']:
        permission_set_detail = sso_admin_client.describe_permission_set(
            InstanceArn=sso_identity_store_arn,
            PermissionSetArn=permission_set
        )
        accounts = sso_admin_client.list_accounts_for_provisioned_permission_set(
            InstanceArn=sso_identity_store_arn,
            PermissionSetArn=permission_set
        )
        for account in accounts["AccountIds"]:
            aws_config += f'[profile {permission_set_detail["PermissionSet"]["Name"]}-{account}]\n'
            aws_config += f'sso_start_url = {sso_portal_url}\n'
            aws_config += f'sso_region ={sso_region}\n'
            aws_config += f'sso_account_id = {account}\n'
            aws_config += f'sso_role_name = {permission_set_detail["PermissionSet"]["Name"]}\n'
            aws_config += f'region = {sso_region}\n'
            aws_config += '\n'

    f = open(os.path.expanduser('~') + "/.aws/config", "w")
    f.write(aws_config)
    f.close()
    #print(aws_config)