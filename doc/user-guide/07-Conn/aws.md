
##  Connector type: aws

The **aws** connector manages access to AWS access keys. It supports static
access keys as well as session credentials obtained by assuming an IAM role in
either the current AWS account or another account.

!!! note
    IAM assumed role session credentials are new in version 8.1 (Kīlauea).

When used with [redshift_unload](#job-type-redshift_unload) jobs,
this connector provides the access keys that are used in the S3 `AUTHORIZATION`
parameters in the `UNLOAD` command.

When used with [db_from_s3](#job-type-db_from_s3) jobs,
this connector provides the access keys that are used to provide the database
the required access to S3 to load the data.

When used with [exe](#job-type-exe) and
[pkg](#job-type-pkg) jobs, it provides an environment variable
pointing to a script that will run the AWS CLI with an appropriate AWS
authentication profile.

|Field|Type|Required|Description|
|-|-|-|-------------------------------------------------------------|
|access\_keys|String|Note 1|The name of an encrypted SSM parameter containing the access keys. For a given `<REALM>`, the SSM parameter name must be of the form `/lava/<REALM>/...`. The value must be in the format `access_key_id,access_secret_key` and must be a **secure string** encrypted using the `lava-<REALM>-sys` KMS key.|
|conn\_id|String|Yes|Connection identifier.|
|description|String|No|Description.|
|duration|Duration|No|The duration of a session created when an IAM role is assumed. Defaults to the value of the [AWS_CONN_DURATION](#configuration-for-the-aws-connector) configuration parameter. As AWS credentials are cached, it is critical that this is significantly longer than the cache duration as specified by the [AWS_ACCESS_KEY_CACHE_TTL](#configuration-for-the-aws-connector) parameter.|
|enabled|Boolean|Yes|Whether or not the connection is enabled.|
|external\_id|String|No|Name of an SSM parameter containing an external ID to use when assuming a role to obtain session credentials. While AWS does not consider this to be a sensitive security parameter, it is stored in the SSM parameter store for ease of management. It is still recommended to use a secure parameter. Can't hurt.|
|policy\_arns|String \| List[String]|No|The ARNs of IAM managed policies to use as managed session policies. The policies must exist in the same account as the role. The session permissions are the intersection of these policies and the policies of the role being assumed. It is not possible to expand the underlying role permissions.|
|policy|Map[String,\*]|No|An IAM policy to use as an inline session policy. The value must be a fully-formed AWS IAM policy. The session permissions are the intersection of the specified policy and the policies of the role being assumed. It is not possible to expand the underlying role permissions.|
|region|String|No|The AWS region name. If not specified, the current region is assumed.|
|role\_arn|String|Note 1|The ARN of an IAM role to assume to obtain session credentials.|
|tags|Map[String,String]|No|A map of session tags to pass. See [Tagging Amazon Web Services STS Sessions](https://docs.aws.amazon.com/IAM/latest/UserGuide/id_session-tags.html).|
|type|String|Yes|`aws`.|

Notes:

1.  One of `access_keys` or `role_arn` must be specified.

2.  If a `role_arn` is specified, The trust policy on the role must allow it to
    be assumed by the lava worker. If session tags are specified using the `tags`
    field, the trust policy must also permit this.

3.  When assuming a role, the lava worker will set the role session name. By
    default, this is in the form `lv-<REALM>-<JOB-ID>`, cleansed as necessary to
    satisfy the requirements for session names. (See the `CONN_APP_NAME`
    [worker configuration parameter](#general-configuration-parameters).)

### Using the AWS Connector in Shell Scripts { data-toc-label="Use in Shell Scripts" }

The **aws** connector creates a small shell script that is a wrapper around the
AWS CLI that handles the access keys. The shell script is a drop in replacement
for the AWS CLI when used in lava jobs.

Consider the following [exe](#job-type-exe) job:

```json
{
    "description": "Show usage of aws CLI connector in a shell script",
    "enabled": true,
    "job_id": "aws-cli-example",
    "parameters": {
        "connections": {
            "aws1": "aws-conn-id-1",
            "aws2": "aws-conn-id-2"
        }
    },
    "payload": "example/aws-cli-conn.sh",
    "type": "exe",
    "worker": "core"
}

```

The `connections` element in the `parameters` will result in lava preparing
connector shell scripts whose names are placed in the environment variables
`LAVA_CONN_AWS1` and `LAVA_CONN_AWS2` respectively.

The payload (`example/aws-cli-conn.sh` in this example) can then use these
scripts just like the AWS CLI. For example:

```bash
#!/bin/bash

$LAVA_CONN_AWS1 sts get-caller-identity

$LAVA_CONN_AWS2 s3 ls
```

### Using the AWS Connector in Python { data-toc-label="Use in Python" }

!!! note
    New in version 8.1 (Kīlauea).

Python jobs can call the lava connector subsystem directly via the lava API.


Consider the following [exe](#job-type-exe) job:

```json
{
    "description": "Show usage of aws CLI connector in a Python program",
    "enabled": true,
    "job_id": "aws-python-example",
    "parameters": {
        "connections": {
            "aws3": "aws-conn-id-3"
        }
    },
    "payload": "example/aws-cli-conn.py",
    "type": "exe",
    "worker": "core"
}

```

Once again, lava will create a shell script accessed via the `LAVA_CONN_AWS3`
environment variable. It will also populate the `LAVA_CONNID_AWS3` environment
variable with the connection ID. This can be used with the lava connector API to
obtain a boto3
[Session](https://boto3.amazonaws.com/v1/documentation/api/latest/reference/core/session.html)
object, thus:


```python
import os
from lava.connection import get_aws_session

realm = os.environ['LAVA_REALM']

# Note we want the connection ID, not the CLI script here.
conn_id = os.environ['LAVA_CONNID_AWS3']

# Use the lava API to the connection subsystem to obtain a boto3 Session.
aws_session = get_aws_session(conn_id, realm)

sts = aws_session.client('sts')
print(sts.get_caller_identity())

```

!!! note
    A Python script _can_ use the CLI script as well (e.g. via the
    [subprocess](https://docs.python.org/3/library/subprocess.html) module) but
    why would you want to?
