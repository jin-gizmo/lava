
## Connector type: ssh, scp, sftp

This group of connectors provides support for the SSH family of clients.

When used with [exe](#job-type-exe) and
[pkg](#job-type-pkg) jobs, each connector provides an
environment variable pointing to a script that will run the corresponding CLI
with SSH keys managed in the background.

|Field|Type|Required|Description|
|-|-|-|-------------------------------------------------------------|
|conn\_id|String|Yes|Connection identifier.|
|description|String|No|Description.|
|enabled|Boolean|Yes|Whether or not the connection is enabled.|
|ssh\_key|String|Yes|The name of an encrypted SSM parameter containing the SSH private key. There **must not** be any passphrase on the key. For a given `<REALM>`, the SSM parameter name must be of the form `/lava/<REALM>/...` and the value must be a **secure string** encrypted using the `lava-<REALM>-sys` KMS key.|
|ssh_options|List\[String]|No|A list of SSH options as per **ssh_config(5)**. e.g. `StrictHostKeyChecking=no`|
|type|String|Yes|`ssh`, `sftp` or `scp`.|

The process for saving an SSH private key in the SSM parameter store using the
 AWS CLI looks like this:

```bash
# Create a new SSH key
ssh-keygen -f mykey

# Upload the private key to the SSM parameter store. Here realm name is "dev"
aws ssm put-parameter --name "/lava/dev/ssh01/ssh-key"  \
    --description "SSH key for ssh01" \
    --type SecureString \
    --value "$(cat mykey)" \
    --key-id alias/lava-dev-sys
```
