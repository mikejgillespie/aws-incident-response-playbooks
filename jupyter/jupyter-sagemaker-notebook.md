# SageMaker
SageMaker notebooks provide a simple way to host the Jupyter Notebook, 
A cloudformation template is included in this repo to create a Jupyter notebook instance with the correct permissions.

There are two ways to configure the notebook server for multiple account access. You can use IAM Identity Center for SSO support, or configure role assumption permissions. 

## IAM Identity Center (SSO)
To set IAM Identity Center permissions, provide values for the **SsoRegion** and **SsoUrl** parameters:
* **SsoRegion**: The region the SSO instance is running
* **SsoUrl**: The URL to connect to the SSO instance
* **DefaultRole**: The ARN of the role this notebook server should default to in the format: arn:aws:iam::AWS_ACCOUNTID:role/PERMISSION_SET_NAME

```
aws cloudformation deploy --capabilities CAPABILITY_IAM --template-file jupyter-instance.yaml --parameter-overrides SsoRegion=<SSO_REGION> SsoUrl=<SSO_URL> DefaultRole=arn:aws:iam::AWS_ACCOUNTID:role/PERMISSION_SET_NAME --stack-name sso-jupyter-notebook
```
## IAM Role Assumption
Alternatively, provide the roles that this instance will have access to assume
* **LinkedRoles**: A comma separated list of the ARN of roles this notebook server has access to
* **DefaultRole**: The ARN of the role this notebook server should default to

```
aws cloudformation deploy --capabilities CAPABILITY_IAM --template-file jupyter-instance.yaml --parameter-overrides LinkedRoles=arn1,arn2,arn3 DefaultRole=arn:aws:iam::AWS_ACCOUNTID:role/RoleName --stack-name sso-jupyter-notebook
```
