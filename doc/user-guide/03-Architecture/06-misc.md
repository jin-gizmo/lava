
## Auxiliary Components

### IAM Roles and Permissions

The realm [CloudFormation templates](#building-the-cloudformation-templates)
will create a base set of IAM components, both for the lava workers and for
users needing to interact with the lava environment.  See [Lava IAM
Components](#lava-iam-components).

### KMS Keys

Each realm requires two AWS KMS keys:

1. `lava-<REALM>-sys`: The system key that should be used for things such as
    credentials when stored in the SSM parameter store. Workers need to be able
    to decrypt using this key.

2.  `lava-<REALM>-user`: The user key that should be used for encrypting data in
    the S3 bucket for the realm. Workers need to be able to encrypt and decrypt
    with this key. 

These keys are created by the [CloudFormation
templates](#lava-installation-and-operation).

### SSM Parameters

Lava [connectors](#connectors) that require access to
confidential parameters (e.g. passwords) expect to find those in the AWS SSM
parameter store with names starting with `/lava/<REALM>/`. Secure string
parameters should use the `lava-<REALM>-sys` KMS key.

### SNS Topics

Lava [job actions](#job-actions) can send SNS messages at the
completion of a job. While the standard worker IAM policy does not prevent
access to other topics, the [CloudFormation
templates](#lava-installation-and-operation) create a topic
`lava-<REALM>-notices` for general purpose notices.
