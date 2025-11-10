
## Connector type: oracle

The **oracle** connector handles connections to Oracle databases.

|Field|Type|Required|Description|
|-|-|-|-------------------------------------------------------------|
|conn\_id|String|Yes|Connection identifier.|
|database|String|No*|A deprecated synonym for `sid`.|
|description|String|No|Description.|
|edition|String|No|Oracle version for compatibility in the form `x.y[.z]`.|
|enabled|Boolean|Yes|Whether or not the connection is enabled.|
|host|String|Yes*|The database host DNS name or IP address.|
|password|String|Yes*|The name of an encrypted SSM parameter containing the password. For a given `<REALM>`, the SSM parameter name must be of the form `/lava/<REALM>/...` and the value must be a **secure string** encrypted using the `lava-<REALM>-sys` KMS key.|
|port|Number|Yes*|The database port number.|
|secret_id|String|No|Obtain missing fields from AWS Secrets Manager. [More information](#database-authentication-using-aws-secrets-manager).|
|service\_name|String|No*|The Oracle data base service name. Generally exactly one of `service_name` or `sid` must be specified.|
|sid|String|No*|The Oracle System Identifier of the database. Generally exactly one of `service_name` or `sid` must be specified.|
|type|String|Yes|`oracle`.|
|user|String|Yes*|Database user name.|

!!! info
    Fields with a **Required** column marked with `*` can have a value provided
    directly in the connection specification or indirectly via AWS Secrets
    Manager using the `secret_id` field.  See [Database Authentication Using AWS
    Secrets Manager](#database-authentication-using-aws-secrets-manager) for
    more information.

When used with [exe](#job-type-exe) and
[pkg](#job-type-pkg) job types, the connection is implemented by
the [SQL\*Plus
CLI](https://docs.oracle.com/en/database/oracle/oracle-database/18/sqpug/toc.htm),
`sqlplus`.  Apart from the connection parameters, it is invoked with the
following options:

```bash
sqlplus -NOLOGINTIME -L -S -C <version>
```

The SQL\*Plus CLI is a particularly contrary beast. It is important to explicitly
exit the CLI using an `EXIT` command at the end of any session or else it will
drop into interactive mode and sit there waiting for further commands until the
job reaches its timeout and is killed by lava. A safer approach is to send
commands to the connector via stdin, thus:

```bash
# Assume our conn_id is ora

$LAVA_CONN_ORA <<!
SELECT whatever FROM whichever;
!
```

When used with [sql](#job-type-sql) jobs, do not terminate the
SQL with a semi-colon or a syntax error results.

When used with [sqlc](#job-type-sqlc) jobs, SQL commands must be
terminated with a semi-colon or either a syntax error or no output will result.

### Security Warnings

Oracle CLI clients, including `sqlplus`, do not provide any means to automate
login to the database without specifying the password on the command line. This
means the password is exposed in a process listing. **Do not** use the
**oracle** command line connector on any worker that has multi-user access.

The **oracle** connector does not currently support SSL/TLS.
