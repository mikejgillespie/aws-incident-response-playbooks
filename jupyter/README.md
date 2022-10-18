# Using Jupyter for Incident Response
Jupyter notebooks are typically thought of as a platform for data science and machine learning, but are simply a web-based platform to execute and document code. This feature makes them an excellent platform for running incident response runbook, because often times incident response amounts to gathering and interpreting data, which is the strength of the Jupyter Notebook platform. The goal is to automated the tedious task of gathering data, presenting the data to an analyst, and providing procedures and next steps for the findings. For responses that are simple to automate, those can be done with code blocks in then notebook, and for more complex remediations, the instructions can provide direction on how to handle the scenario.

The notebooks included in this repository combine automation in the form of python code cells and documentation with Markdown. Code in a Jupyter notebook can be executed step-by-step, allowing the user to interact with AWS and non-AWS resources through API calls and data visualized with graphs and charts. The incident response runbooks included in the Jupyter section differ from others in the repository because they depend on configurations within the account to simplify the automation. For example, having all of the organization CloudTrail logs in a specific Athena table means the same notebook can be used across accounts.

* **Opinionated**: The configuration of the AWS account and organization is opionated in order to allow the same scripts to be executed across many accounts. A CloudFormation template is included to configure the management account to have the proper account setup.
* **SSO Authentication**: This solution uses IAM Identity Center for authentication of users. This eliminates the need to grant bread access to the notebook server and permissions within a notebook can be scoped down to what is needed for the response.
* **Notebook Server** The notebooks in this repositiry can use either SageMaker Notebooks or local Jupyter notebooks. A CloudFormation template is included to create a SageMaker Notebook server with the proper permissions.

# Prerequisites
This project assumes the accounts are organized with AWS organizations and authentication is managed by AWS Identity Center (Formerly SSO).


# Installation
First, clone the repo so you have a local copy.

## Account Configuration
In order for the scripts to execute successfully, the account and organization must be configured to run the notebooks. Follow the steps to configure the account:

1. Identify the account and region that is hosting your AWS Identity Center. 
1. Find the IAM Identity Center instance arn. You can find this by going to:
https://us-east-1.console.aws.amazon.com/singlesignon/identity/home?region=us-east-1#!/settings
  * **Note, replace us-east-1 if your Identity center region is different than us-east-1**
  * The ARN us under the details section.
  * The **AWS access portal URL** is in the Identity source section below, and **Identity store ID** is also in the Identity source section.
1. Either upload the `sso-environment.yaml` file to the CloudFormation console, or use the CLI command below to create the stack.
1. If your have a delegate account for CloudFormation organization stack sets, put that 12 digit AWS account id in the **CFN_ACCOUNT_ID** otherwise use the management account.
1. If your have a logging account for CloudFormation organization stack sets, put that 12 digit AWS account id in the **LOGGING_ACCOUNT_ID** otherwise use the management account.
```
aws cloudformation deploy --stack-name sso-config --capabilities CAPABILITY_IAM --parameter-overrides SsoDirectory=IDENTITY_SOURCE_ID SsoPortalUrl=PORTAL_URL SsoInstanceArn=IDENTITYINSTANCE_ARN CfnDelegateAccount=CFN_ACCOUNT_ID LoggingAccount=LOGGING_ACCOUNT_ID --template-file sso-environment.yaml
```

The `sso-environment.yaml` template will configure the following resources: 
* SSO Permission Sets
  * **ViewOnly** Read Only Access to accounts
  * **SysAdmin** Systems Administrator access
  * **Administrator** Full Administrator access. Use only in break-glass scenarios.
* Parameters
  * S3 Bucket
  * SSO Instance ID
  * SSO Instance Arn

This will only create the permission sets. If you don't have them already, you will have to create users and groups in your Identity Center. Then you will to associate the AWS account with the permission sets and users/groups. 

* https://docs.aws.amazon.com/singlesignon/latest/userguide/addusers.html
* https://docs.aws.amazon.com/singlesignon/latest/userguide/addgroups.html
* https://aws.amazon.com/premiumsupport/knowledge-center/create-sso-permission-set


## Create a Jupyter Server
There are two options you can choose from, either use a SageMaker notebook instance, or you can create a local notebook server.

### SageMaker
The SageMaker notebooks should be deployed to the same account and region as the IAM Identity Center.

A cloudformation template is included in this repo to create a Jupyter notebook instance with the correct permissions.

```
aws cloudformation deploy --stack-name sso-jupyter --capabilities CAPABILITY_IAM --template-file jupyter-notebook-instance.yaml
```

Skip ahead to **Configuring The Jupyter Lab Server**

### Local
The machine will need access to the [AWS CLI 2](https://docs.aws.amazon.com/cli/latest/userguide/getting-started-install.html), and the default profile has access to the management account of IAM Identity Center.

Identity Center Permissions
* sso:ListPermissionSets
* sso:ListAccountsForProvisionedPermissionSet
* sso:DescribePermissionSet

SSM Permissions:
The notebook server will need `GetParameter` permissions on the following SSM Parameters:
* Jupyter-SSO-Directory
* Jupyter-SSO-Portal-Url
* Jupyter-SSO-Instance-Arn
* Jupyter-S3

S3
The notebook server will need the following access to the shared S3 bucket for the Notebooks. The name of the Bucket is an ssm parameter in S3.
* s3:GetObject
* s3:PutObject
* s3:ListBucket


**Mac / Linux**



The Jupyter server can be installed using pip.
```
pip install jupyterlab
```

Then run the Jupyter Lab server:
```
jupyter-lab
```
**Windows**
Install Pip if it isn't already installed:
```
curl https://bootstrap.pypa.io/get-pip.py -o get-pip.py
python get-pip.py
```
Install the CLI v2:
```
msiexec.exe /i https://awscli.amazonaws.com/AWSCLIV2.msi
```

then install jupyterlab and 
```
pip install jupyterlab boto3
```

### Configuring The Jupyter Lab Server
Once the notebook server is running and you are logged into JupyterLab, you can drag and drop the `configure-notebook-server.ipynb`  and `jupyter_aws_sso.py` files into the file explorer on the left side.

Double click on the configure-notebook-server.ipynb and follow the instructions. This setup only needs to be done one time.

**Enhancement: The notebook server can be automated to automatically run a notebook. We can configure the notebook to load the notebook and execute it, skipping these two manual steps.**

From this point, any notebook that starts with will these two lines of code will initiate the SSO login.
```
import jupyter_aws_sso
jupyter_aws_sso.login(role, aws_account)
```
