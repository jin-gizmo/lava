
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
|ssl_ca_file|String|No|The location of a file containing a host certificate in PEM format for the database server. This can be a local file or a URI. Any of the schemes supported by [smart_open](https://pypi.org/project/smart-open/) can be used (e.g. `s3://`, `http://`, `https://` etc).|
|ssl_mode|String|No|Enable SSL/TLS. Must be one of `require`, `verify-ca`, `verify-full`. If not specified, SSL/TLS may or may not be enabled (depending on driver defaults). See also [SSL/TLS for Database Connectors](#ssltls-for-database-connectors).|
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

!!! warning
    The MariaDB `mysql` CLI cannot properly handle the `verify-ca` mode. If no
    certificate is provided, it will effectively drop back to `require` mode. To
    force a valid certificate to be provided (either explicitly via a
    certificate file or implicitly via a publicly signed host certificate),
    `verify-full` mode is required. This will also enforce host name matching,
    which may not be what is desired.
