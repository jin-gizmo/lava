
## Connector type: mysql

The **mysql** connector handles connections to MySQL compatible databases.

|Field|Type|Required|Description|
|-|-|-|-------------------------------------------------------------|
|ca\_cert|String|No|The name of a file containing the CA certificate for the database server. Ignored unless `ssl` is `true`.|
|conn\_id|String|Yes|Connection identifier.|
|description|String|No|Description.|
|database|String|Yes*|The name of the database (schema) within the database server.|
|enabled|Boolean|Yes|Whether or not the connection is enabled.|
|host|String|Yes*|The database host DNS name or IP address.|
|password|String|Yes*|The name of an encrypted SSM parameter containing the password. For a given `<REALM>`, the SSM parameter name must be of the form `/lava/<REALM>/...` and the value must be a **secure string** encrypted using the `lava-<REALM>-sys` KMS key.|
|port|Number|Yes*|The database port number.|
|preserve\_case|Boolean|No|If `true`, don't fold database object names to lower case when quoting them for use in [db_from_s3](#job-type-db_from_s3) jobs. The default is `false` (i.e. case folding is enabled).|
|secret_id|String|No|Obtain missing fields from AWS Secrets Manager. [More information](#database-authentication-using-aws-secrets-manager).|
|ssl|Boolean|No|Set to `true` to enable SSL. Default is `false`.|
|type|String|Yes|`mysql`.|
|user|String|Yes*|Database user name.|

!!! info
    Fields with a **Required** column marked with `*` can have a value provided
    directly in the connection specification or indirectly via AWS Secrets
    Manager using the `secret_id` field.  See [Database Authentication Using AWS
    Secrets Manager](#database-authentication-using-aws-secrets-manager) for
    more information.

When used with [exe](#job-type-exe) and
[pkg](#job-type-pkg) job types, the connection is implemented by
the `mysql` CLI, either the MySQL Community version, or the MariaDB version,
depending on the variant installed on the worker. These have some minor CLI
parameter differences which lava manages for the connection parameters. Apart
from the connection parameters, it is invoked with the following options:

```bash
mysql --batch --connect-timeout=10
```
