
## Connector type: postgres

The **postgres** connector handles connections to Postgres compatible databases.

|Field|Type|Required|Description|
|-|-|-|-------------------------------------------------------------|
|conn\_id|String|Yes|Connection identifier.|
|database|String|Yes*|The name of the database within the database server.|
|description|String|No|Description.|
|enabled|Boolean|Yes|Whether or not the connection is enabled.|
|host|String|Yes*|The database host DNS name or IP address.|
|password|String|Yes*|The name of an encrypted SSM parameter containing the password. For a given `<REALM>`, the SSM parameter name must be of the form `/lava/<REALM>/...` and the value must be a **secure string** encrypted using the `lava-<REALM>-sys` KMS key.|
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
