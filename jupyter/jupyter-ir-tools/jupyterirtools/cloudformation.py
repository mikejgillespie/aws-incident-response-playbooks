import os
import boto3 
import subprocess
import shlex

from . import sso

def deploy(stack_name, role, account, template, capabilities="CAPABILITY_IAM", region='us-east-1', parameters = {}):
    session = sso.get_session(role, account)
    
    profile = f"{role}-{account}"
    
    cmd = f"aws cloudformation deploy --stack-name={stack_name} --template-file {template} --capabilities {capabilities} --profile {profile}"
    
    params = ""
    for key in parameters:
        params += f" {key}={parameters[key]}"
    
    if params != "":
        cmd += f" --parameter-overrides {params}"
    
    print(cmd)
    process = subprocess.Popen(shlex.split(cmd), stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    link = ""
    
    cnt = 0
    
    while True:
        cnt+=1
        rc = process.poll()
        
        output = process.stdout.readline()
        while output:
            txt_output = output.strip().decode('utf-8')
            print(f"{txt_output}")
            output = process.stdout.readline()
        
        std_error = process.stderr.read()
        while std_error:
            txt_error = std_error.strip().decode('utf-8')
            print(f"{txt_error}")
            std_error = process.stderr.read()
            
        if rc is not None:
            break

            
    retval = {
        "Name": stack_name,
        "Outputs": {}
    }
    
    
    if rc == 0:
        cloudformation_client = session.client('cloudformation')
        cfn_response = cloudformation_client.describe_stacks(StackName=stack_name)
        if len(cfn_response['Stacks']) > 0:
            stack = cfn_response['Stacks'][0]
            retval["Status"] = stack["StackStatus"]
            if 'Outputs' in stack:
                for output in stack['Outputs']:     
                    retval["Outputs"][output['OutputKey']] = output['OutputValue']
    
    return retval