# SageMaker
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