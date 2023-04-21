import boto3
import json
from jupyterirtools import sso
from IPython.display import display, Markdown, Latex, HTML
from datetime import datetime
import os

cached_org_accounts = []

def cloudtrail_s3_events(org_root_account, active_regions, role):
    results = []
    
    org_accounts = get_org_accounts()
    
    for client, account, region in sso.get_client_by_account_region(role, 'cloudtrail', org_accounts, active_regions):

        response = client.describe_trails()
        trail = response['trailList'][0]

        selectors = client.get_event_selectors(TrailName=trail['TrailARN'])

        s3_data_events = False
        if 'AdvancedEventSelectors' in selectors:
            for selector in selectors['AdvancedEventSelectors']:
                for field_selectors in selector['FieldSelectors']:
                    if field_selectors['Field'] == 'resources.type' and field_selectors['Equals'][0] == 'AWS::S3::Object':
                        s3_data_events = True
                        result  += f"|<span style=\"color:green\"> &#9679;</span>|ENABLED|S3 Data Events.|{account}|{region}|\n"
        results.append({
            "S3 Data Events": "ENABLED" if s3_data_events else "NOT ENABLED",
            "Account": account,
            "Region": region
        })

    display_results_status("Evaluating Cloudtrail S3 Data Events", results,  lambda x: 1 if x['S3 Data Events'] == "ENABLED" else 3)
               

        
def check_org_trail(org_root_account, role, active_regions):


    results = []
    
    
    org_accounts = get_org_accounts()
    session = sso.get_session(role,org_root_account)

    cloudtrail_client = boto3.client('cloudtrail')

    response = cloudtrail_client.describe_trails()
    trails = response['trailList']

    exist_org_trail = False
    for trail in trails:
        if trail['IsOrganizationTrail']:
            exist_org_trail = True

    central_bucket_name = trails[0]['S3BucketName']

    results.append({
        "Trail": "ENABLED" if exist_org_trail else "NOT ENABLED",
        "Name": "Organizational Trail",
        "Account": org_root_account,
        "Region": session.region_name
    })
    if not exist_org_trail:
        all_accounts_centralized = True
        for client, account, region in sso.get_client_by_account_region(role, 'cloudtrail', org_accounts, active_regions):
            list_trails_response = client.describe_trails()
            central_bucket = False
            for local_trail in list_trails_response['trailList']:
                if local_trail['S3BucketName'] == central_bucket_name:
                    central_bucket = True

            results.append({
                "Trail": "ENABLED" if central_bucket else "NOT ENABLED",
                "Name": "Account/Region Trail",
                "Account": account,
                "Region": region
            })
            
    display_results_status("Evaluating Organization Cloudtrail", results,  lambda x: 1 if x['Trail'] == "ENABLED" else 3)

def check_guardduty(active_regions, role):
    results = []

    org_accounts = get_org_accounts()
    
    for client, account, region in sso.get_client_by_account_region(role, 'guardduty', org_accounts, active_regions):
        response = client.list_detectors()
        results.append({
            "GuardDuty": "ENABLED" if len(response['DetectorIds']) > 0 else "NOT FOUND",
            "Account": account,
            "Region": region
        })
            
    display_results_status("Evaluating AWS GuardDuty", results,  lambda x: 1 if x['GuardDuty'] == "ENABLED" else 3)
    
def check_aws_config(active_regions, role):
    results = []
    
    org_accounts = get_org_accounts()

    for client, account, region in sso.get_client_by_account_region(role, 'config', org_accounts, active_regions):
        response = client.describe_configuration_recorder_status()
        results.append({
            "Config Recorder": "ENABLED" if len(response['ConfigurationRecordersStatus']) > 0 else "DISABLED",
            "Account": account,
            "Region": region
        })

    display_results_status("Evaluating AWS Config Recorders", results,  lambda x: 1 if x['Config Recorder'] == "ENABLED" else 3)
            
def get_org_accounts():
    global cached_org_accounts
    
    if len(cached_org_accounts) > 0:
        return cached_org_accounts
    
    orgs_client = boto3.client('organizations')

    cached_org_accounts = []

    for account in orgs_client.list_accounts()['Accounts']:
        cached_org_accounts.append(account['Id'])

    return cached_org_accounts

def inspector_check_organization(active_regions, role):
    results = []
    
    org_accounts = get_org_accounts()
    

    region_map = {}
    LOGGING = 2
    
    for region in active_regions:
        delegated_admin_account = ""
        for account in org_accounts:
            session = sso.get_session(role, account, region)
            inspector2_client = session.client('inspector2', region_name = region)
            try:
                response = inspector2_client.get_delegated_admin_account()
                
                if delegated_admin_account == "":
                    #print(response['delegatedAdmin']['accountId'])
                    delegated_admin_account = response['delegatedAdmin']['accountId']
                    if LOGGING <= 1:
                        results.append({
                            "Inspector2": "ACTIVE",
                            "Account": account,
                            "Region": region
                        })
            except inspector2_client.exceptions.ValidationException as error:
                if LOGGING <= 1:
                         results.append({
                            "Inspector2": "ACTIVE",
                            "Account": account,
                            "Region": region
                        })
                        
        if delegated_admin_account != "":
            region_map[region] = delegated_admin_account
            results.append({
                "Inspector2": "ACTIVE",
                "Account": account,
                "Region": region
            })
        else:
            results.append({
                "Inspector2": "INACTIVE",
                "Account": account,
                "Region": region
            })
    display_results_status("Evaluating Amazon Inspector2 activation", results,  lambda x: 1 if x['Inspector2'] == "ACTIVE" else 3)

    results = []
    
    for k in region_map:
        session = sso.get_session(role, region_map[k], k)
        inspector_client = session.client('inspector2', region_name = k)
        response = inspector_client.list_coverage(filterCriteria = {
            'resourceType': [
                {
                    'comparison': 'EQUALS',
                    'value': 'AWS_EC2_INSTANCE'
                }
            ]
        })

        for resource in response['coveredResources']:
            results.append({
                "Scan Status": resource['scanStatus']['statusCode'],
                "Resource Id": resource['resourceId'],
                "Instance Name": resource['resourceMetadata']['ec2'].get('tags',{}).get('Name', ''),
                "Account": resource['accountId'],
                "Region": k
            })

    display_results_status("Inspector Instance Status", results,  lambda x: 1 if x['Scan Status'] == "ACTIVE" else 3)

        
def check_patch_manager(active_regions, role):
    results = [] 

    org_accounts = get_org_accounts()
    for client, account, region in sso.get_client_by_account_region(role, 'ssm', org_accounts, active_regions):
        session = sso.get_session(role, account,region)
        ec2_client = session.client('ec2', region_name = region)
        
        paginator = ec2_client.get_paginator('describe_instances').paginate()
        for page in paginator:
            instanceIds = []
            for reservation in page['Reservations']:
                for instance in reservation['Instances']:
                    instanceIds.append(instance['InstanceId'])
        
            response = client.describe_instance_patch_states(InstanceIds=instanceIds)
            #print(response)
            for state in response['InstancePatchStates']:
                results.append({
                    "Instance ID": state['InstanceId'],
                    "Patch Group": state['PatchGroup'],
                    "CriticalNonCompliantCount": state['CriticalNonCompliantCount'],
                    "Account": account,
                    "Region": region
                })
        
    display_results_status("Evaluating SSM Patch Manager activation", results,  lambda x: 1 if x['CriticalNonCompliantCount'] == 0 else 3)
    
            
def check_public_ips(configuration_aggregator):
    config_client = boto3.client('config')

    response = config_client.select_aggregate_resource_config(
        Expression="""
    SELECT
      configuration.attachment.instanceId,
      accountId,
      awsRegion,
      configuration.association.publicIp,
      availabilityZone,
      relationships
    WHERE
      resourceType = 'AWS::EC2::NetworkInterface'
      and relationships.resourceType = 'AWS::EC2::Instance'
      AND configuration.association.publicIp > '0.0.0.0'    
    """,
        ConfigurationAggregatorName=configuration_aggregator
    )

    results = []

    for result in response['Results']:
        item = json.loads(result)

        results.append({
            "accountId": item['accountId'],
            "awsRegion": item['awsRegion'],
            "instanceId": item['configuration']['attachment']['instanceId'],
            "publicIp": item['configuration']['association']['publicIp']
        })
    display_results_status("Public IPs", results)

    
def check_restricted_ssh_config_rule(configuration_aggregator, role, active_regions):
    config_client = boto3.client('config')
    org_accounts = get_org_accounts()
    
    results = []
    
    rule_name = ""
    paginator = config_client.get_paginator('describe_organization_config_rules')
    for page in paginator.paginate():
        for rule in page['OrganizationConfigRules']:
            if rule['OrganizationManagedRuleMetadata']['RuleIdentifier'] == "INCOMING_SSH_DISABLED":
                rule_name = rule['OrganizationConfigRuleName']
    
    if rule_name != "":
        response = config_client.describe_organization_config_rules(
            OrganizationConfigRuleNames=[rule_name]
        )
        results.append({"ResourceType": "organization_config_rule","ResourceId": rule_name, "ComplianceType": "COMPLIANT"})
                        
        response = config_client.describe_aggregate_compliance_by_config_rules(
            ConfigurationAggregatorName=configuration_aggregator,
        )

        org_restricted_ssh_rule = ""

        for rule in response['AggregateComplianceByConfigRules']:
            if rule['ConfigRuleName'].startswith("OrgConfigRule-org-restricted-ssh"):
                org_restricted_ssh_rule = rule['ConfigRuleName']
                
                
        for client, account, region in sso.get_client_by_account_region(role, 'ssm', org_accounts, active_regions):
        
            response = config_client.get_aggregate_compliance_details_by_config_rule(
                ConfigurationAggregatorName=configuration_aggregator,
                ConfigRuleName=org_restricted_ssh_rule,
                ComplianceType='NON_COMPLIANT',
                AccountId=account,
                AwsRegion=region
            )

            for result in response['AggregateEvaluationResults']:
                results.append({
                    "ResourceType": result['EvaluationResultIdentifier']['EvaluationResultQualifier']['ResourceType'],
                    "ResourceId": result['EvaluationResultIdentifier']['EvaluationResultQualifier']['ResourceId'],
                    "ComplianceType": result['ComplianceType'],
                    "AccountId": result['AccountId'],
                    "AwsRegion": result['AwsRegion']
                })        
        
    else:
        results.append({"config-rule": "org-restricted-ssh", "ComplianceType": "There is not an org-wide rule for restricted-ssh. Strongly suggest that you add one"})
    
    display_results_status("Restricted SSHs", results, lambda x: 1 if x['ComplianceType'] == 'COMPLIANT' else 3)

def save_report(destination_bucket, destination_prefix):
    script = """
this.nextElementSibling.focus();
this.dispatchEvent(new KeyboardEvent('keydown', {key:'s', keyCode: 83, metaKey: true}));
"""
    display(HTML((
        '<img src onerror="{}" style="display:none">'
        '<input style="width:0;height:0;border:0">'
    ).format(script)))

    s3path = f's3://{destination_bucket}/{destination_prefix}ransomware-preparedness.{datetime.now().strftime("%m%d%Y%H%M%S")}.html'

    os.system('jupyter nbconvert --to html ransomware-preparedness.ipynb')
    os.system(f'aws s3 cp ransomware-preparedness.html {s3path}')
    os.system('rm ransomware-preparedness.html')

def display_results_status(title, results, f = lambda x: 1):
    display(Markdown(f"### {title}")) 
    
    headers = ["status"]
    for result in results:
        for k in result:
            if not k in headers:
                headers.append(k)
                

    grid = "|"
    for header in headers:
        grid += f"{header}|"
    grid += f"\n|"
    for header in headers:
        grid += f"-----|"
        
    grid += f"\n"  
    
    for result in results:
        r = f(result)
        
        first = True
        grid += f"|"
        
        for header in headers:
            if first:
                color = "red"
                if r == 1:
                     color = "green"
                elif r == 2:
                     color = "orange"

                grid += f"<span style=\"color:{color}\"> &#9679;</span>|"
                first = False
            elif header in result:
                grid += f"{result[header]}|"
            else: 
                grid += f"&nbsp;|"
        grid += f"\n"
   
    display(Markdown(grid)) 