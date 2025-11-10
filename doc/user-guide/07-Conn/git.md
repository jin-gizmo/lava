
##  Connector type: git

The **git** connector manages access to Git repositories by providing support
for managing SSH private keys.

When used with [exe](#job-type-exe) and
[pkg](#job-type-pkg) jobs, it provides an environment variable
pointing to a script that will run the Git CLI with SSH keys managed in the
background.

Note that only SSH access to repositories is supported. HTTPS is not supported.

|Field|Type|Required|Description|
|-|-|-|-------------------------------------------------------------|
|conn\_id|String|Yes|Connection identifier.|
|description|String|No|Description.|
|enabled|Boolean|Yes|Whether or not the connection is enabled.|
|ssh\_key|String|Yes|The name of an encrypted SSM parameter containing the SSH private key. There **must not** be any passphrase on the key. For a given `<REALM>`, the SSM parameter name must be of the form `/lava/<REALM>/...` and the value must be a **secure string** encrypted using the `lava-<REALM>-sys` KMS key. Refer to the [ssh connector](#connector-type-ssh-scp-sftp) for more information on how to prepare and store the key.|
|ssh_options|List\[String]|No|A list of SSH options as per **ssh_config(5)**. e.g. `StrictHostKeyChecking=no`|
|type|String|Yes|`git`.|
