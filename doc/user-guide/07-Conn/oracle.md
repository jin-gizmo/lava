
## Connector type: oracle

The **oracle** connector handles connections to Oracle databases.

!!! note
    As of v8.3 (Mauna Loa), the obsolete `cx_Oracle` driver has been replaced
    with its successor,
    [python-oracledb](https://oracle.github.io/python-oracledb/). Oracle claims
    it is backward compatible.


|Field|Type|Required|Description|
|-|-|-|-------------------------------------------------------------|
|conn\_id|String|Yes|Connection identifier.|
|database|String|No*|A deprecated synonym for `sid`.|
|description|String|No|Description.|
|edition|String|No|Oracle version for compatibility in the form `x.y[.z]`.|
|enabled|Boolean|Yes|Whether or not the connection is enabled.|
|host|String|Yes*|The database host DNS name or IP address.|
|password|String|Yes*|The name of an encrypted SSM parameter containing the password. For a given `<REALM>`, the SSM parameter name must be of the form `/lava/<REALM>/...` and the value must be a **secure string** encrypted using the `lava-<REALM>-sys` KMS key.|
|port|Number|Yes*|The database port number. The conventional ports for Oracle are 1521 for TCP (no SSL/TLS) and 2484 for TCPS (SSL/TLS).|
|secret_id|String|No|Obtain missing fields from AWS Secrets Manager. [More information](#database-authentication-using-aws-secrets-manager).|
|service\_name|String|No*|The Oracle data base service name. Generally, exactly one of `service_name` or `sid` must be specified.|
|sid|String|No*|The Oracle System Identifier of the database. Generally, exactly one of `service_name` or `sid` must be specified.|
|ssl_ca_file|String|No|The location of a file containing a host certificate in PEM format for the database server. This can be a local file or a URI. Any of the schemes supported by [smart_open](https://pypi.org/project/smart-open/) can be used (e.g. `s3://`, `http://`, `https://` etc). Supported in [thin mode](#through-thick-and-thin) only.|
|ssl_mode|String|No|Enable SSL/TLS. Must be one of `require` ([thin mode](#through-thick-and-thin) only), `verify-ca`, `verify-full`. If not specified, SSL/TLS is not enabled. See also [SSL/TLS for Database Connectors](#ssltls-for-database-connectors).|
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

### Through Thick and Thin

The [python-oracledb](https://oracle.github.io/python-oracledb/) driver can
operate in either *thin* or *thick* mode. The default thin mode does not require
the Oracle client libraries whereas thick mode does. The old `Cx_Oracle` only
supported thick mode.

The lava worker will use thin mode by default but can be configured to use
thick mode. See
[Configuration for the oracle Connector](#configuration-for-the-oracle-connector).

!!! note
    The [lava AMI](#the-lava-ec2-ami)
    and *full* [lava docker images](#docker-images-for-lava) still contain the
    Oracle client libraries as they are required for the **SQL\*Plus** CLI used
    by the [sqlc](#job-type-sqlc) job type.

Programs using the lava API to connect to an Oracle database should very rarely
require thick mode, but can engage it like so:

```python
import oracledb
import os

from lava.connection import get_pysql_connection

# We start in thin mode.
assert oracledb.is_thin_mode()
# For thick mode, we must switch before establishing any connections.
# Add lib_dir=... argument if libraries are not in a standard location.
oracledb.init_oracle_client()
assert not oracledb.is_thin_mode()

conn = get_pysql_connection(
    conn_id=os.environ['LAVA_CONNID_MY_ORACLE_DB'],
    realm=os.environ['LAVA_REALM']
)
# We can also confirm thick/thin-ness from a connection without needing to
# import oracldb.
assert not conn.thin
```

#### SSL / TLS in Thick and Thin Modes

SSL / TLS behaviour differs between thin and thick mode.

In thin mode, the
security is managed by Python using the
[ssl](https://docs.python.org/3/library/ssl.html) module. All of the lava
`ssl_mode` values (`require` / `verify-ca` / `verify-full`) are available.
A custom host certificate can be provided via the `ssl_ca_file` connection
attribute.

In thick mode, the security is managed by the Oracle client
libraries. The only `ssl_mode` setting supported is `verify-full` and a custom
certificate cannot be provided. The thick mode limitations also apply to the
[sqlc](#job-type-sqlc) job type when used with the Oracle connector.

### Security Warnings

Oracle CLI clients, including `sqlplus`, do not provide any means to automate
login to the database without specifying the password on the command line. This
means the password is exposed in a process listing. **Do not** use the
**oracle** command line connector on any worker that has multi-user access.

The **oracle** connector does not currently support SSL/TLS.
