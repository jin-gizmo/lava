
## Connector type: redshift-serverless

This is the connector for Redshift Serverless clusters.

|Field|Type|Required|Description|
|-|-|-|-------------------------------------------------------------|
|conn\_id|String|Yes|Connection identifier.|
|database|String|Yes*|The name of the database within the Redshift Serverless namespace.|
|description|String|No|Description.|
|enabled|Boolean|Yes|Whether or not the connection is enabled.|
|external_id|String|No|Name of an SSM parameter containing an external ID to use when assuming the IAM role specified by `role_arn` when [generating temporary IAM user credentials](#creating-temporary-iam-user-credentials-for-redshift-serverless). While AWS does not consider this to be a sensitive security parameter, it is stored in the SSM parameter store for ease of management. It is still recommended to use a secure parameter. Can't hurt.|
|host|String|Yes*|The Redshift serverless workgroup endpoint address.|
|password_duration|String|No|The password duration when [generating temporary IAM user credentials](#creating-temporary-iam-user-credentials-for-redshift-serverless) in the form `nnX` where `nn` is a number and `X` is `s` (seconds), `m` (minutes) or `h` (hours). If not specified, the [default worker configuration](#configuration-for-the-redshift-serverless-connector) is used. Limits imposed by the Redshift Serverless [GetCredentials](https://docs.aws.amazon.com/redshift-serverless/latest/APIReference/API_GetCredentials.html) API apply.|
|password|String|No*|The name of an encrypted SSM parameter containing the password. For a given `<REALM>`, the SSM parameter name must be of the form `/lava/<REALM>/...` and the value must be a **secure string** encrypted using the `lava-<REALM>-sys` KMS key. If not specified, the worker will attempt to [generate temporary IAM user credentials](#creating-temporary-iam-user-credentials-for-redshift-serverless).|
|port|Number|Yes*|The Redshift serverless workgroup port number.|
|preserve\_case|Boolean|No|If `true`, don't fold database object names to lower case when quoting them for use in [db_from_s3](#job-type-db_from_s3) jobs. The default is `false` (i.e. case folding is enabled).|
|role\_arn|String|No|The ARN of an IAM role that will be assumed when [generating temporary IAM user credentials](#creating-temporary-iam-user-credentials-for-redshift-serverless).|
|secret_id|String|No|Obtain missing fields from AWS Secrets Manager. [More information](#database-authentication-using-aws-secrets-manager).|
|ssl|Boolean|No|Set to `true` to enable SSL. Default is `false`.|
|subtype|String|No|Specifies the underlying DBAPI 2.0 driver. See [Redshift Connector Subtypes](#redshift-connector-subtypes) below.|
|type|String|Yes|`redshift-serverless`.|
|user|String|Yes*|Database user name.|
|workgroup|String|No|The name of the workgroup associated with the database. This is used when [generating temporary IAM user credentials](#creating-temporary-iam-user-credentials-for-redshift-serverless). If required and not specified, the first component of the `host` field is used.|

!!! info
    Fields with a **Required** column marked with `*` can have a value provided
    directly in the connection specification or indirectly via AWS Secrets
    Manager using the `secret_id` field.  See [Database Authentication Using AWS
    Secrets Manager](#database-authentication-using-aws-secrets-manager) for
    more information.

#### Redshift Serverless Connector Subtypes

The `subtype` field of the connection specification allows selection of different
database drivers.

|Subtype|Description|
|-|-----------------|
|pg8000|[Pg8000](https://pypi.org/project/pg8000/) is the default if no subtype is specified.|
|redshift|This is the [AWS Redshift connector](https://pypi.org/project/redshift-connector/).|

#### Creating Temporary IAM User Credentials for Redshift Serverless

!!! note
    The AWS documentation on this leaves a lot to be desired.

If a password is not obtained from the `password` field or secrets manager, lava
will attempt to use the Redshift Serverless
[GetCredentials](https://docs.aws.amazon.com/redshift-serverless/latest/APIReference/API_GetCredentials.html)
API to generate temporary IAM-based database user credentials.

Unlike the Redshift provisioned
[GetClusterCredentials](https://docs.aws.amazon.com/redshift/latest/mgmt/generating-iam-credentials-steps.html)
API, the Redshift Serverless
[GetCredentials](https://docs.aws.amazon.com/redshift-serverless/latest/APIReference/API_GetCredentials.html)
API does not allow the target database user name to be specified. The username
is derived automatically from the IAM principal as follows:

*   For IAM users, the database username is `IAM:<IAM-USER-NAME>`.

*   For IAM roles, the database username is `IAMR:<IAM-ROLE-NAME>`.

If the user does not already exist in the database, it will be automatically
created and given access to the public schema. This is daft but that's how it is.
The user can be created manually or given additional database permissions via
the normal GRANT mechanism, as required.

This can be very limiting in terms of fine grained access control from lava to
Redshift. To provide some flexibility, the Redshift Serverless connector can
assume a different IAM role prior to generating database access credentials by
specifying the `role_arn` (and optional `external_id`) elements in the
connection specification. The assumed role is then the one that will determine
the database user name.

For example, assume the lava worker normally operates under the IAM role
`lava-prod-worker-core`. If no `role_arn` is specified, the database user will
be `IAMR:lava-dev-worker-core`.

If `role_arn` is `arn:aws:iam::123456789123:role/rs01`, the database user will
be `IAMR:rs01`.

The IAM policy attached to the `lava-dev-worker-core` role will need to contain
something like this:

```json
"Statement": [
    {
        "Sid": "AssumeRoleForRedshiftServerlessAccess"
        "Effect": "Allow",
        "Action": "sts:AssumeRole",
        "Resource": [
            "arn:aws:iam::123456789123:role/rs01"
        ]
    }
]
```

The IAM policy attached to the `rs01` role will need to contain something like
this:

```json
"Statement": [
    {
        "Sid": "GetRedshiftServerlessCreds",
        "Effect": "Allow",
        "Action": "redshift-serverless:GetCredentials",
        "Resource": [
            "arn:aws:redshift-serverless:ap-southeast-2:123456789123:workgroup/3741886a-223d-446f-a77c-a5d0e7b5ad32"
        ]
    }
]
```

The trust policy for the `rs01` role will need to contain the elements necessary
to allow it to be assumed by `lava-dev-worker-core`.

!!! note
    Lava currently does not cache temporary credentials. Watch out for throttling
    on the `GetCredentials` API.
