
## Connector type: postgres-aurora

This connector support AWS RDS Aurora PostgreSQL clusters. This is almost a
synonym for [postgres](#connector-type-postgres).
Key differences are:
 
*   The [db_from_s3](#job-type-db_from_s3) job can take
    advantage of an AWS facility to load data directly from S3.

*   [Database authentication using IAM credential generation](#creating-temporary-iam-user-credentials-for-aws-rds-aurora-postgresql)
    is supported.

|Field|Type|Required|Description|
|-|-|-|-------------------------------------------------------------|
|conn\_id|String|Yes|Connection identifier.|
|database|String|Yes*|The name of the database within the database server.|
|description|String|No|Description.|
|enabled|Boolean|Yes|Whether or not the connection is enabled.|
|host|String|Yes*|The database host DNS name or IP address.|
|password|String|No*|The name of an encrypted SSM parameter containing the password. For a given `<REALM>`, the SSM parameter name must be of the form `/lava/<REALM>/...` and the value must be a **secure string** encrypted using the `lava-<REALM>-sys` KMS key. If not specified, the worker will attempt to [generate temporary IAM user credentials](#creating-temporary-iam-user-credentials-for-aws-rds-aurora-postgresql).|
|port|Number|Yes*|The database port number.|
|preserve\_case|Boolean|No|If `true`, don't fold database object names to lower case when quoting them for use in [db_from_s3](#job-type-db_from_s3) jobs. The default is `false` (i.e. case folding is enabled).|
|secret_id|String|No|Obtain missing fields from AWS Secrets Manager. [More information](#database-authentication-using-aws-secrets-manager).|
|ssl|Boolean|No|Set to `true` to enable SSL. Default is `false`|
|subtype|String|No|Specifies the underlying DBAPI 2.0 driver. The default is `pg8000` which should be used wherever possible. The `pygresql` driver is also available.|
|type|String|Yes|`psql` or `postgres`.|
|user|String|Yes*|Database user name.|

!!! info
    Fields with a **Required** column marked with `*` can have a value provided
    directly in the connection specification or indirectly via AWS Secrets
    Manager using the `secret_id` field.  See [Database Authentication Using AWS
    Secrets Manager](#database-authentication-using-aws-secrets-manager) for
    more information.

When used with [exe](#job-type-exe) and
[pkg](#job-type-pkg) job types, the connection is implemented by
the `psql` CLI.  Apart from the connection parameters, it is invoked with the
following options:

```bash
psql --no-psqlrc --quiet --set ON_ERROR_STOP=on --pset footer=off
```

### Creating Temporary IAM User Credentials for AWS RDS Aurora PostgreSQL { data-toc-label="IAM Auth for Aurora PostgreSQL" }

If the `password` field is not present in the connection specification, lava
will attempt to
[generate temporary IAM credentials](https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/UsingWithRDS.IAMDBAuth.html) using the `generate-db-auth-token` mechanism.

The specified user must already exist in the database. Enable IAM authentication
for a user thus:

```sql
CREATE USER a_user; 
GRANT rds_iam TO a_user;
```

!!! info
    SSL is mandatory when using temporary IAM user credentials.

### Psql CLI Password Limitations

The psql CLI will not accept passwords in a PGPASS file (or entered
interactively) that are longer than a certain (undocumented) length. IAM based
authentication for RDS involves temporary passwords that are much longer than
this limit.

To workaround this limitation, lava has to put long passwords into an
environment variable. While this is not ideal from a security perspective, at
least the passwords are short lived.
