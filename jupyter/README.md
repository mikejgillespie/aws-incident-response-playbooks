# Using Jupyter for Incident Response
Jupyter notebooks are typically thought of as a platform for data science and machine learning, but are simply a web-based platform to execute and document code. This feature makes them an excellent platform for running incident response runbook, because often times incident response amounts to gathering and interpreting data, which is the strength of the Jupyter Notebook platform. The goal is to automated the tedious task of gathering data, presenting the data to an analyst, and providing procedures and next steps for the findings. For responses that are simple to automate, those can be done with code blocks in then notebook, and for more complex remediations, the instructions can provide direction on how to handle the scenario.

The notebooks included in this repository combine automation in the form of python code cells and documentation with Markdown. Code in a Jupyter notebook can be executed step-by-step, allowing the user to interact with AWS and non-AWS resources through API calls and data visualized with graphs and charts. The incident response runbooks included in the Jupyter section differ from others in the repository because they depend on configurations within the account to simplify the automation. For example, having all of the organization CloudTrail logs in a specific Athena table means the same notebook can be used across accounts.

* **Opinionated**: The configuration of the AWS account and organization is opionated in order to allow the same scripts to be executed across many accounts. A CloudFormation template is included to configure the management account to have the proper account setup.

* **Multi-account**: The runbooks can be configured to run in a single or multi-account mode.

* **Notebook Server** The notebooks in this repositiry can use either SageMaker Notebooks or local Jupyter notebooks. A CloudFormation template is included to create a SageMaker Notebook server with the proper permissions.  

# Option 1: Quick Start
The quick start will provide access to a SageMaker Jupyter notebook that downloads the notebook files in this repository. Once the notebook is available, it will be accessible through the SageMaker console. **Note**: The quick start only provides read-only access and Athena query access to AWS. If a notebook has remediatiation step, the notebook will not have permissions unless explicitly granted.

1. Download this CloudFormation [Template](cfn-templates/sso-jupyter-server.yaml)
1. All parameters are optional, accept the default parameters.
1. Accept the IAM resources will be created.
1. Find the Notebook server in the SageMaker [console](https://console.aws.amazon.com/sagemaker/home?#/notebook-instances)

# Option 2: Multi-Account Configuration
In order to run your notebooks across accounts, you will need to choose the cross-account authentication method:
1. **IAM Identity Center (Preferred)**: Use this method if you have IAM Identity Center SSO configured in your AWS Organization.
1. **Cross-Account Role Assumptions**: Use this method if you do not have IAM Identity Center SSO.

See details below on choosing and configuring the multi-account permissions.

## Steps:
### Clone the Repo
Clone this repo to get a copy of the source code locally.

### Configure the authentication method
The first consideration is if the runbooks will be run in a single account or cross account. The single account method is the simplest, as it doesn't require any cross account permissions. However, in some notebooks there may be a need to run across accounts in an organization, but only the existing account will be accessable. The notebooks will work, they just won't be able to collect data across accounts.

### Single Account
For a single account, the cloudformation script will grant the permissions needed in the local account. Nothing more is needed.

### Multiple Account
It is a best practice to use AWS Organizations to manage the collection of accounts. If you are using AWS Organizations and IAM Identity Center, this is the best way to authenticate the Jupyter Notebook context.

#### IAM Identity Center (Formerly SSO) Configuration
In order for the scripts to execute successfully, the account and organization must be configured to have resources available for the notebooks to gather data such as CloudTrail logs and VPC Flow Logs. Follow the steps to configure the account:

1. Identify the account and region that is hosting your AWS Identity Center. 
1. Find the IAM Identity Center instance arn. You can find this by going to:
https://us-east-1.console.aws.amazon.com/singlesignon/identity/home?region=us-east-1#!/settings
  * **Note, replace us-east-1 if your Identity center region is different than us-east-1**
  * The **AWS access portal URL** is in the Identity source section below, and **Identity store ID** is also in the Identity source section.
  * Either upload the `sso-environment.yaml` file to the CloudFormation console, or use the CLI command below to create the stack. There are no parameters to this file.
 * AWS CLI Command:   
```
aws cloudformation deploy --stack-name sso-config --capabilities CAPABILITY_IAM --template-file sso-environment.yaml
```

The `sso-environment.yaml` template will configure the following **SSO Permission Sets**:
  * **ViewOnly** Read Only Access to accounts
  * **SysAdmin** Systems Administrator access
  * **Administrator** Full Administrator access. Use only in initial setup and break-glass scenarios.

**Next Step**
Associate the AWS accounts with the permission sets and users/groups. 

* https://docs.aws.amazon.com/singlesignon/latest/userguide/addusers.html
* https://docs.aws.amazon.com/singlesignon/latest/userguide/addgroups.html
* https://aws.amazon.com/premiumsupport/knowledge-center/create-sso-permission-set


####  Instance Profile + Cross-Account Role Assumption
Is IAM identity center is not an option, then you can deploy the the roles using an AWS cloudformation stackset. This can be done using AWS Organizations (preferred) or explicity listing the accounts.

The `non-sso-account.yaml` configures the three roles for the notebooks, and grants permission for the role assumption.

### Create a Jupyter Server
There are two options you can choose from, either use a SageMaker notebook instance, or you can create a local notebook server.

* [Local Jupyter Notebook](jupyter-localserver.md)
* [SageMaker Notebook](jupyter-sagemaker-notebook.md)

## Verifying The Jupyter Lab Server

Enter into the jupyter folder of this repository - it should be loaded in the jupyter file navigator.

Double click on the [configure-notebook-server.ipynb](configure-notebook-server.ipynb) and follow the instructions to verify the notebook configuration. This setup only needs to be done one time.


From this point, any notebook that loads the jupyterauth module will initialize the permissions.
```
from jupyterirtools import jupyterauth
```


## Configure the AWS Organizations

Lastly, check the configuration of the logs using  [check-organization-readiness](check-organization-readiness.ipynb) notebook.

### Security Considerations for non-organizations accounts
This creates a trust relationship between the Jyputer account and the non-sso accounts. Thus, any user or role that has access to call sts:AssumeRole in the Jump account can assume the role in the non-sso account.

