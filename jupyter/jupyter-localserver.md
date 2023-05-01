### MacOS
**Start in the project directory**

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

Add these lines to your ~/.zshrc file for zsh and ~/.bash_profile for bash. Note: The jump account is used to assume roles in non-AWS Organizations accounts, see section 'Optional - Include accounts outside the AWS Organization'.
```
export SSO_URL=<SSO LOGIN URL>
export SSO_REGION=<SSO REGION>
```

Restart your terminal window so these changes take effect.

```
cd jupyter
pip install -e jupyter-ir-tools
```

Then run the Jupyter Lab server:
```
jupyter-lab
```

### Windows

**Start in the project directory**

Install Pip if it isn't already installed:
```
curl https://bootstrap.pypa.io/get-pip.py -o get-pip.py
python get-pip.py
```
Install the CLI v2:
```
msiexec.exe /i https://awscli.amazonaws.com/AWSCLIV2.msi
```

Set the environment variables for the SSO environment. Note: The jump account is used to assume roles in non-AWS Organizations accounts, see section 'Optional - Include accounts outside the AWS Organization'.
```
setx SSO_URL <SSO LOGIN URL>
setx SSO_REGION <SSO REGION>
```

then install jupyterlab and 
```
pip install jupyterlab boto3 pyathena
```

```
cd jupyter
pip install -e jupyter-ir-tools
```

Run jupyter:
```
jupyter-lab
```