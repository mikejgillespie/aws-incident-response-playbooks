# Using Jupyter for Incident Response
* Opinionated
* Uses SSO for authentication
* Can use SageMaker or local Jupyter

# Installation
First, clone the repo so you have a local copy.

## Account Configuration
In order for the scripts to execute successfully, the account and organization must be configured to run the notebooks.

First, identify the account and region that is hosting your AWS Identity Center. 

Next, you need to find the IAM Identity Center instance arn. You can find this by going to:
https://us-east-1.console.aws.amazon.com/singlesignon/identity/home?region=us-east-1#!/settings

**Note, replace us-east-1 if your Identity center region is different than us-east-1**

The ARN us under the details section.
The **AWS access portal URL** is in the Identity source section below, and **Identity store ID** is also in the Identity source section.


Either upload the `sso-environment.yaml` file to the CloudFormation console, or use the CLI command below to create the stack.

```
aws cloudformation deploy --stack-name sso-config --capabilities CAPABILITY_IAM --parameter-overrides SsoDirectory=IDENTITY_SOURCE_ID SsoPortalUrl=PORTAL_URL SsoInstanceArn=IDENTITYINSTANCE_ARN --template-file sso-environment.yaml
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

Once the notebook is running and you are logged into JupyterLab, you can drag and drop the `configure-notebook-server.ipynb`  and `jupyter_aws_sso.py` files into the file explorer on the left side.

Double click on the configure-notebook-server.ipynb and follow the instructions. This setup only needs to be done one time.

**TODO: The notebook server can be automated to automatically run a notebook. We can configure the notebook to load the notebook and execute it, automated these two steps.**

From this point, any notebook that starts with will initiate the SSO login.
```
import jupyter_aws_sso
jupyter_aws_sso.login(role, aws_account)
```

### Local

#### Mac

#### Windows