# Using Jupyter for Incident Response
Jupyter notebooks are typically thought of as a platform for data science and machine learning, but are simply a web-based platform to execute and document code. This feature makes them an excellent platform for running incident response runbook, because often times incident response amounts to gathering and interpreting data, which is the strength of the Jupyter Notebook platform. The goal is to automated the tedious task of gathering data, presenting the data to an analyst, and providing procedures and next steps for the findings. For responses that are simple to automate, those can be done with code blocks in then notebook, and for more complex remediations, the instructions can provide direction on how to handle the scenario.

The notebooks included in this repository combine automation in the form of python code cells and documentation with Markdown. Code in a Jupyter notebook can be executed step-by-step, allowing the user to interact with AWS and non-AWS resources through API calls and data visualized with graphs and charts. The incident response runbooks included in the Jupyter section differ from others in the repository because they depend on configurations within the account to simplify the automation. For example, having all of the organization CloudTrail logs in a specific Athena table means the same notebook can be used across accounts.

* **Opinionated**: The configuration of the AWS account and organization is opionated in order to allow the same scripts to be executed across many accounts. A CloudFormation template is included to configure the management account to have the proper account setup.
* **SSO Authentication**: This solution uses IAM Identity Center for authentication of users. This eliminates the need to grant bread access to the notebook server and permissions within a notebook can be scoped down to what is needed for the response.
* **Notebook Server** The notebooks in this repositiry can use either SageMaker Notebooks or local Jupyter notebooks. A CloudFormation template is included to create a SageMaker Notebook server with the proper permissions.

# Prerequisites
This project assumes the accounts are organized with:
* **AWS Organizations**
* **IAM Identity Center (Formerly SSO)**


# Installation
1. Clone the repo for a local copy
1. Configure the **IAM Identity Center (Formerly SSO)**. See next section
1. Create a Create a Jupyter Server instance either locally or using **SageMaker Notebooks**.
1. Configure the **AWS Organizations** settings using the [Configure AWS Organzations](configure-aws-organizations.ipynb) notebook.

### Clone the Repo
Clone this repo to get a copy of the source code locally.

### IAM Identity Center (Formerly SSO) Configuration
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


### Create a Jupyter Server
There are two options you can choose from, either use a SageMaker notebook instance, or you can create a local notebook server.

#### SageMaker
The SageMaker notebooks should be deployed to the same account and region as the IAM Identity Center.

A cloudformation template is included in this repo to create a Jupyter notebook instance with the correct permissions.

**Parameters**:
* **SsoRegion**: The region the SSO instance is running
* **SsoUrl**: The URL to connect to the SSO instance
* **LoggingAccount**: The AWS Account ID for the logging account
* **ManagementAccount**: The AWS Account ID for the management account

```
aws cloudformation deploy --capabilities CAPABILITY_IAM --template-file sso-jupyter-server.yaml --parameter-overrides SsoRegion=<SSO_REGION> SsoUrl=<SSO_URL> LoggingAccount=<LOGGING_ACCOUNT> ManagementAccount=<MANAGEMENT_ACCOUNT> --stack-name sso-jupyter-notebook
```

Skip ahead to **Verifying The Jupyter Lab Server**

#### Local
The machine will need access to the [AWS CLI 2](https://docs.aws.amazon.com/cli/latest/userguide/getting-started-install.html), and the default profile has access to the management account of IAM Identity Center.

Identity Center Permissions
* sso:ListPermissionSets
* sso:ListAccountsForProvisionedPermissionSet
* sso:DescribePermissionSet

SSM Permissions:
The notebook server will need `GetParameter` permissions on the following SSM Parameters:
* Jupyter-*

S3
The notebook server will need the following access to the shared S3 bucket for the Notebooks. The name of the Bucket is an ssm parameter in S3.
* s3:GetObject
* s3:PutObject
* s3:ListBucket


##### MacOS

If the AWS CLI v2 is not installed:
```
curl "https://awscli.amazonaws.com/AWSCLIV2.pkg" -o "AWSCLIV2.pkg"
sudo installer -pkg AWSCLIV2.pkg -target /
```

The Jupyter server can be installed using pip.
```
pip install jupyterlab boto3 pyathena
```

Add the environment variables to your ~/.bash_profile or ~/.zshrc file depending on which version of MacOS your are running.

Starting with macOS Catalina (10.15), Apple set the default shell to the Z shell (zsh). In previous macOS versions, the default was Bash.

Add these lines to your ~/.zshrc file for zsh and ~/.bash_profile for bash:
```
export LOGGING_ACCOUNT=<LOGGING_ACCOUNT_ID>
export SSO_URL=<SSO LOGIN URL>
export SSO_REGION=<SSO REGION>
export MANAGEMENT_ACCOUNT=<MANAGEMENT_ACCOUNT_ID>
```

Restart your terminal window so these changes take effect.

Then run the Jupyter Lab server:
```
jupyter-lab
```

##### Windows
Install Pip if it isn't already installed:
```
curl https://bootstrap.pypa.io/get-pip.py -o get-pip.py
python get-pip.py
```
Install the CLI v2:
```
msiexec.exe /i https://awscli.amazonaws.com/AWSCLIV2.msi
```

Set the environment variables for the SSO environment
```
setx LOGGING_ACCOUNT <LOGGING_ACCOUNT_ID>
setx SSO_URL <SSO LOGIN URL>
setx SSO_REGION <SSO REGION>
setx MANAGEMENT_ACCOUNT <MANAGEMENT_ACCOUNT_ID>
```

then install jupyterlab and 
```
pip install jupyterlab boto3 pyathena
```
Run jupyter:
```
jupyter-lab
```


#### Verifying The Jupyter Lab Server

Enter into the jupyter folder of this repository - it should be loaded in the jupyter file navigator.

Double click on the configure-notebook-server.ipynb and follow the instructions to verify the notebook configuration. This setup only needs to be done one time.


From this point, any notebook that starts with will these two lines of code will initiate the SSO login.
```
import jupyter_aws_sso
jupyter_aws_sso.login(role, aws_account)
```

## Configure the **AWS Organizations**

Lastly, baseline your AWS organization be executing the [configure-aws-organization](configure-aws-organization.ipynb) notebook.