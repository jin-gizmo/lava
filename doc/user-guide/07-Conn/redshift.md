
## Connector type: redshift

This is the connector for Redshift provisioned clusters. It can also be used for
Redshift Serverless clusters **except** when IAM generated user credentials are
used. In that case, the [redshift-serverless](#connector-type-redshift-serverless)
connector must be used.

This connector is similar to [postgres](#connector-type-postgres). Note
that some operations are specific to Redshift and are not supported on
conventional Postgres databases (e.g. the `COPY` and `UNLOAD` commands).

|Field|Type|Required|Description|
|-|-|-|-------------------------------------------------------------|
|cluster\_id|String|No|The Redshift cluster identifier. If required and not specified, the first component of the `host` name is used.|
|conn\_id|String|Yes|Connection identifier.|
|database|String|Yes*|The name of the database within the database server.|
|description|String|No|Description.|
|enabled|Boolean|Yes|Whether or not the connection is enabled.|
|host|String|Yes*|The database host DNS name or IP address.|
|password_duration|String|No|The password duration when [generating temporary IAM user credentials](#creating-temporary-iam-user-credentials-for-redshift) in the form `nnX` where `nn` is a number and `X` is `s` (seconds), `m` (minutes) or `h` (hours). If not specified, the [default worker configuration](#configuration-for-the-redshift-connector) is used. Limits imposed by the [GetClusterCredentials](https://docs.aws.amazon.com/redshift/latest/mgmt/generating-iam-credentials-steps.html) API apply.|
|password|String|No*|The name of an encrypted SSM parameter containing the password. For a given `<REALM>`, the SSM parameter name must be of the form `/lava/<REALM>/...` and the value must be a **secure string** encrypted using the `lava-<REALM>-sys` KMS key. If not specified, the worker will attempt to [generate temporary IAM user credentials](#creating-temporary-iam-user-credentials-for-redshift).|
|port|Number|Yes*|The database port number.|
|preserve\_case|Boolean|No|If `true`, don't fold database object names to lower case when quoting them for use in [db_from_s3](#job-type-db_from_s3) jobs. The default is `false` (i.e. case folding is enabled).|
|secret_id|String|No|Obtain missing fields from AWS Secrets Manager. [More information](#database-authentication-using-aws-secrets-manager).|
|ssl|Boolean|No|Set to `true` to enable SSL. Default is `false`.|
|subtype|String|No|Specifies the underlying DBAPI 2.0 driver. See [Redshift Connector Subtypes](#redshift-connector-subtypes) below.|
|type|String|Yes|`redshift`.|
|user|String|Yes*|Database user name.|

!!! info
    Fields with a **Required** column marked with `*` can have a value provided
    directly in the connection specification or indirectly via AWS Secrets
    Manager using the `secret_id` field.  See [Database Authentication Using AWS
    Secrets Manager](#database-authentication-using-aws-secrets-manager) for
    more information.

#### Redshift Connector Subtypes

The `subtype` field of the connection specification allows selection of different
database drivers.

|Subtype|Description|
|-|-----------------|
|pg8000|[Pg8000](https://pypi.org/project/pg8000/) is the default if no subtype is specified.|
|redshift|This is the [AWS Redshift connector](https://pypi.org/project/redshift-connector/).|

!!! info
    As of version 8.1 (Kīlauea), the Redshift connector no longer supports
    PyGreSQL. This is not a lava change. PyGreSQL just doesn't work with
    Redshift any more.

#### Creating Temporary IAM User Credentials for Redshift

If the `password` field is not present in the connection specification, lava
will attempt to use the Redshift
[GetClusterCredentials](https://docs.aws.amazon.com/redshift/latest/mgmt/generating-iam-credentials-steps.html)
API to generate temporary IAM-based database user credentials.

The specified user must already exist in the database as lava (deliberately)
does not support `AutoCreate` of users.

Lava will specify the target cluster ID, database and target user in the
credentials request. This means that the IAM policy attached to the worker will
need to contain an element something like this:

```json
"Statement": [
    {
        "Sid": "GetRedshiftCreds",
        "Effect": "Allow",
        "Action": "redshift:GetClusterCredentials",
        "Resource": [
            "arn:aws:redshift:ap-southeast-2:123456789012:dbuser:cluster_id/target_user",
            "arn:aws:redshift:ap-southeast-2:123456789012:dbname:cluster_id/mydb"
        ]
    }
]
```

!!! info
    Lava currently does not cache temporary credentials. Watch out for
    throttling on the `GetClusterCredentials` API.
