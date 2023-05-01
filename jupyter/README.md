# Using Jupyter for Incident Response
Jupyter notebooks are typically thought of as a platform for data science and machine learning, but are simply a web-based platform to execute and document code. This feature makes them an excellent platform for running incident response runbook, because often times incident response amounts to gathering and interpreting data, which is the strength of the Jupyter Notebook platform. The goal is to automated the tedious task of gathering data, presenting the data to an analyst, and providing procedures and next steps for the findings. For responses that are simple to automate, those can be done with code blocks in then notebook, and for more complex remediations, the instructions can provide direction on how to handle the scenario.

The notebooks included in this repository combine automation in the form of python code cells and documentation with Markdown. Code in a Jupyter notebook can be executed step-by-step, allowing the user to interact with AWS and non-AWS resources through API calls and data visualized with graphs and charts. The incident response runbooks included in the Jupyter section differ from others in the repository because they depend on configurations within the account to simplify the automation. For example, having all of the organization CloudTrail logs in a specific Athena table means the same notebook can be used across accounts.

* **Opinionated**: The configuration of the AWS account and organization is opionated in order to allow the same scripts to be executed across many accounts. A CloudFormation template is included to configure the management account to have the proper account setup.

* **Multi-account**: The runbooks can be configured to run in a single or multi-account mode.

* **Notebook Server** The notebooks in this repositiry can use either SageMaker Notebooks or local Jupyter notebooks. A CloudFormation template is included to create a SageMaker Notebook server with the proper permissions.  

# Option 1: Quick Start
The quick start will provide access to a SageMaker Jupyter notebook that downloads the notebook files in this repository. Once the notebook is available, it will be accessible through the SageMaker console.

1. Download this CloudFormation [Template](cfn-templates/sso-jupyter-server.yaml)
1. All parameters are optional, accept the default parameters.
1. Accept the IAM resources will be created.
1. Find the Notebook server in the SageMaker [console](https://console.aws.amazon.com/sagemaker/home?#/notebook-instances)

# Option 2: Installation
1. Clone the repo for a local copy
1. Create a Create a Jupyter Server instance either:
  1. [SageMaker Notebook](jupyter-sagemaker-notebook.md) - Simplest and easiest way to get started
  1. [Local Jupyter Notebook](jupyter-localserver.md)
1. Configure the authentication method
  1. Single Account
    1. Instance Profile / IAM User
  1. Multi-Account
    1. AWS Organizations + IAM Identity Center (Formerly SSO)
    1. Instance Profile + Cross-Account Role Assumption
    1. Configure the **AWS Organizations** settings using the [Configure AWS Organzations](configure-aws-organizations.ipynb) notebook.

## Clone the Repo
Clone this repo to get a copy of the source code locally.

## Create a Jupyter Server
There are two options you can choose from, either use a SageMaker notebook instance, or you can create a local notebook server.

* [Local Jupyter Notebook](jupyter-localserver.md)
* [SageMaker Notebook](jupyter-sagemaker-notebook.md)


## Configure the authentication method
The first consideration is if the runbooks will be run in a single account or cross account. The single account method is the simplest, as it doesn't require any cross account permissions. However, in some notebooks there may be a need to run across accounts in an organization, but only the existing account will be accessable. The notebooks will work, they just won't be able to collect data across accounts.

### Single Account
For a single account, simple grant access to the instance profile that runs the Jupyter to assume the 3 roles provided in [non-sso-account.yaml](cfn-templates/non-sso-account.yaml).

```
aws cloudformation deploy --stack-name jupyter-iam-roles --capabilities CAPABILITY_IAM --parameter-overrides NotebookServerIamArn=xx --template-file non-sso-account.yaml
```

#### Multiple Account
It is a best practice to use AWS Organizations to manage the collection of accounts. If you are using AWS Organizations and IAM Identity Center, this is the best way to authenticate the Jupyter Notebook context.

## IAM Identity Center (Formerly SSO) Configuration
In order for the scripts to execute successfully, the account and organization must be configured to have resources available for the notebooks to gather data such as CloudTrail logs and VPC Flow Logs. Follow the steps to configure the account:

1. Identify the account and region that is hosting your AWS Identity Center. 
1. Find the IAM Identity Center instance arn. You can find this by going to:
https://us-east-1.console.aws.amazon.com/singlesignon/identity/home?region=us-east-1#!/settings
  * **Note, replace us-east-1 if your Identity center region is different than us-east-1**
  * The **ARN** us under the details section.
  * The **AWS access portal URL** is in the Identity source section below, and **Identity store ID** is also in the Identity source section.
  * Either upload the `sso-environment.yaml` file to the CloudFormation console, or use the CLI command below to create the stack. **Parameters for CloudFormation stack**:
    1. **SsoDirectory**: The directory ID of the IAM Identity Center directory
    1. **SsoPortalUrl**: The AWS Access Portal url. Found in the IAM Identity Center console
    1. **SsoInstanceArn**: The IAM Identity Center Arn. Found in the IAM Identity Center console
    1. **CfnDelegateAccount**: If your have a delegate account for CloudFormation organization stack sets, set that 12 digit AWS account id, otherwise use the management account.
    1. **LoggingAccount**: If your have a logging account for CloudFormation organization stack sets, put that 12 digit AWS account id, otherwise use the management account.
 * AWS CLI Command:   
```
aws cloudformation deploy --stack-name sso-config --capabilities CAPABILITY_IAM --parameter-overrides SsoDirectory=IDENTITY_SOURCE_ID SsoPortalUrl=PORTAL_URL SsoInstanceArn=IDENTITYINSTANCE_ARN CfnDelegateAccount=CFN_ACCOUNT_ID LoggingAccount=LOGGING_ACCOUNT_ID --template-file sso-environment.yaml
```

The `sso-environment.yaml` template will configure the following resources: 
* SSO Permission Sets
  * **ViewOnly** Read Only Access to accounts
  * **SysAdmin** Systems Administrator access
  * **Administrator** Full Administrator access. Use only in initial setup and break-glass scenarios.
* Parameters
  * S3 Bucket
  * SSO Instance ID
  * SSO Instance Arn
  * CfnDelegateAccount
  * LoggingAccount

**Next Step**
Associate the AWS accounts with the permission sets and users/groups. 

* https://docs.aws.amazon.com/singlesignon/latest/userguide/addusers.html
* https://docs.aws.amazon.com/singlesignon/latest/userguide/addgroups.html
* https://aws.amazon.com/premiumsupport/knowledge-center/create-sso-permission-set


####  Instance Profile + Cross-Account Role Assumption
Is IAM identity center is not an option, then you can deploy the the roles using an AWS cloudformation stackset. This can be done using AWS Organizations (preferred) or explicitylisting the accounts.

TO DO:
* create stack that deploys a stack set to specific OUs, organizational-root-id, or accounts
* grab the instance profile arn from parameter store
* store the list of accounts in parameter store?
* for SSO, there needs to be a base account - maybe just pull the first account from the list?
* Change library from sso to awsauth.
  * Not login... Set role with optional account?



```
aws cloudformation create-stack-set --stack-set-name jupyter-roles --capabilities CAPABILITY_IAM --parameter-overrides SsoDirectory=IDENTITY_SOURCE_ID SsoPortalUrl=PORTAL_URL SsoInstanceArn=IDENTITYINSTANCE_ARN CfnDelegateAccount=CFN_ACCOUNT_ID LoggingAccount=LOGGING_ACCOUNT_ID --template-url non-sso-account.yaml

```



#### Verifying The Jupyter Lab Server

Enter into the jupyter folder of this repository - it should be loaded in the jupyter file navigator.

Double click on the configure-notebook-server.ipynb and follow the instructions to verify the notebook configuration. This setup only needs to be done one time.


From this point, any notebook that starts with will these two lines of code will initiate the SSO login.
```
from jupyterirtools import sso

sso.login(role, aws_account)
```

## Configure the AWS Organizations

Lastly, check the configuration of the logs using  [check-organization-readiness](check-organization-readiness.ipynb) notebook.


This could be useful to have runbooks to help onboard an account into the Organization, or any time the account intentionally resides outside the organization. The runbook sso library will first attempt to assume the SSO role in the account, when that fails, it will then try to assume the role through the 'jump' account. There is no changes in the runbook needed, as the sso library manages all of the role assumption details. Note: Instead of the management account, another account should be designated as the account that non-SSO accounts inherit permissions.

### Parameters:
**JumpAccount**: The central account in the AWS organization used to jump to the non-organizational accounts. If an SSO user has access to a permission set in the jump account, they will then have access to corresponding role created in the non-SSO account.

### Security Considerations for non-organizations accounts
This creates a trust relationship between the jump account and the non-sso account outside of the organization. Thus, any user or role that has access to call sts:AssumeRole in the Jump account can assume the role in the non-sso account.

