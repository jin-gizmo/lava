
## Connector type: mysql-aurora

The **mysql-aurora** connector handles connections to AWS RDS Aurora MySQL
database clusters. This is almost a synonym for
[mysql](#connector-type-mysql). Key differences are:

*   The [db_from_s3](#job-type-db_from_s3) job can take
    advantage of an AWS facility to load data directly from S3.

*   [Database authentication using IAM credential generation](#creating-temporary-iam-user-credentials-for-aws-rds-aurora-mysql) is supported.

|Field|Type|Required|Description|
|-|-|-|-------------------------------------------------------------|
|ca\_cert|String|No|The name of a file containing the CA certificate for the database server. Ignored unless `ssl` is `true`.|
|conn\_id|String|Yes|Connection identifier.|
|description|String|No|Description.|
|database|String|Yes*|The name of the database (schema) within the database server.|
|enabled|Boolean|Yes|Whether or not the connection is enabled.|
|host|String|Yes*|The database host DNS name or IP address.|
|password|String|No*|The name of an encrypted SSM parameter containing the password. For a given `<REALM>`, the SSM parameter name must be of the form `/lava/<REALM>/...` and the value must be a **secure string** encrypted using the `lava-<REALM>-sys` KMS key. If not specified, the worker will attempt to [generate temporary IAM user credentials](#creating-temporary-iam-user-credentials-for-aws-rds-aurora-mysql).|
|port|Number|Yes*|The database port number.|
|preserve\_case|Boolean|No|If `true`, don't fold database object names to lower case when quoting them for use in [db_from_s3](#job-type-db_from_s3) jobs. The default is `false` (i.e. case folding is enabled).|
|secret_id|String|No|Obtain missing fields from AWS Secrets Manager. [More information](#database-authentication-using-aws-secrets-manager).|
|ssl|Boolean|No|Set to `true` to enable SSL. Default is `false`.|
|type|String|Yes|`mysql-aurora`|
|user|String|Yes*|Database user name.|

!!! info
    Fields with a **Required** column marked with `*` can have a value provided
    directly in the connection specification or indirectly via AWS Secrets
    Manager using the `secret_id` field.  See [Database Authentication Using AWS
    Secrets Manager](#database-authentication-using-aws-secrets-manager) for
    more information.

When used with [exe](#job-type-exe) and
[pkg](#job-type-pkg) job types, the connection is implemented by
the `mysql` CLI.  Apart from the connection parameters, it is invoked with the
following options:

```bash
mysql --batch --connect-timeout=10
```

### Creating Temporary IAM User Credentials for AWS RDS Aurora MySQL { data-toc-label="IAM Auth for Aurora MySQL" }

If the `password` field is not present in the connection specification, lava
will attempt to
[generate temporary IAM credentials](https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/UsingWithRDS.IAMDBAuth.html) using the `generate-db-auth-token` mechanism.

The specified user must already exist in the database. Enable IAM
authentication for a user thus:

```sql
CREATE USER a_user IDENTIFIED WITH AWSAuthenticationPlugin AS 'RDS';
```

The IAM policy attached to the worker will need to contain an element something
like this:

```json
"Statement": [
    {
        "Sid": "GetRdsCreds",
        "Effect": "Allow",
        "Action": "rds-db:connect",
        "Resource": [
            "arn:aws:rds-db:ap-southeast-2:123456789012:dbuser:db-JMH2...6KW6Q/a_user"
        ]
    }
]
```

The DB instance ID for use in the IAM policy can be obtained thus:

```bash
aws rds describe-db-instances --db-instance-identifier 'DB_ID' \
     --query 'DBInstances[0].DbiResourceId' --output text
```

!!! info
    SSL is mandatory when using temporary IAM user credentials.
