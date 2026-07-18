
## Database Connectors

Lava provides database connectors for a number of common database types,
including MySQL, Postgres and Oracle.

If used with [sql](#job-type-sql),
[sqlc](#job-type-sqlc),
[sqli](#job-type-sqli),
[sqlv](#job-type-sqlv),
[db_from_s3](#job-type-db_from_s3) and
[redshift_unload](#job-type-redshift_unload) jobs, lava manages
the connection process in the background.

If used with [exe](#job-type-exe),
[pkg](#job-type-pkg) and
[docker](#job-type-docker) jobs, lava provides an environment
variable pointing to a script that will connect to the database to run SQL. The
executable in the job payload can run the script to access the database without
worrying about managing database connectivity.

Python programs in job payloads can access the lava connector subsystem
directly to obtain either a DBAPI 2.0 connection object or an SQLAlchemy engine
object. Refer to [Developing Lava Jobs](#developing-lava-jobs)
for more information.

### Database Authentication Using AWS SSM Parameter Store { data-toc-label="Auth Using SSM Parameters" }

The database connectors typically require a number of connection and
authentication parameters to be specified, such as:

*   host name
*   port
*   user name
*   password.

These can be defined explicitly in the connection specification, except for the
password. By default, the value of this field is interpreted as the name of an
encrypted SSM parameter that contains the actual password.

The standard lava worker IAM policies will provide read access to SSM parameters
with names of the form `/lava/<REALM>/*`. These must be encrypted with the realm
KMS key `lava-<REALM>-sys`.

### Database Authentication Using AWS Secrets Manager { data-toc-label="Auth Using Secrets Manager" }

The lava database connectors support the AWS Secrets Manager as an alternative
source for some of the connection specification parameters where they are not
provided directly in the specification.

If the connection specification contains a `secret_id` field, a field in the
named secret will be used to populate a missing component in the connector
specification.

Note that Secrets Manager and lava use slightly different naming conventions
for fields. Lava will map Secrets Manager fields to lava fields automatically
using the following translation:

|Secrets Manager Field|Lava Field|
|----|----|
|dbClusterIdentifier|description|
|dbname|database|
|host|host|
|password|password|
|port|port|
|serviceName|service_name|
|sid|sid|
|username|user|

The standard lava worker IAM policies will provide read access to secrets with
names of the form `/lava/<REALM>/*`. These must be encrypted with the realm KMS
key `lava-<REALM>-sys`.

### Database Authentication Using IAM Credential Generation { data-toc-label="Auth Using IAM" }

Some AWS database types provide an IAM based mechanism for obtaining temporary
database credentials. Lava supports this mechanism for some connectors. The
mechanism will be used where the connection specification (after inclusion of
any AWS Secrets Manager components) does not contain a password.

Refer to individual connector details for more information.

### SSL/TLS for Database Connectors { data-toc-label="SSL/TLS" }

!!! note
    SSL / TLS support for database connectors has been significantly improved
    across most of the database connectors in v8.3 (Mauna Loa).

Some database connectors support the use of SSL/TLS for connection encryption
and, optionally, host authentication. SSL/TLS based client authentication is not
supported.

Implementation details may vary by database and driver type. Unless otherwise
indicated in the sections on individual connectors, those that do support
SSL/TLS use the following attributes in the connection specification.

*   `ssl_mode`: If set, enable SSL/TLS. If not set, SSL/TLS is not explicitly
    enabled by lava. It is up to the underlying driver, which may, or may not,
    use SSL/TLS by default. You should assume the worst.

    The value of `ssl_mode` must be one of the following.

    |Value|Description|
    |-|-|
    |require|SSL/TLS will be enabled. Neither the host certificate nor the hostname will be verified. This was the mode supported on SSL enabled connections prior to v8.3 (Mauna Loa).|
    |verify-ca|SSL/TLS will be enabled. The host certificate will be validated but the hostname will not be.|
    |verify-full|SSL/TLS will be enabled. The host certificate and hostname will be validated.|


*   `ssl_ca_file`: The location of a file containing a host certificate in PEM
    format for the database server. This can be a local file or a URI. Any of
    the schemes supported by [smart_open](https://pypi.org/project/smart-open/)
    can be used (e.g. s3://, http://, https:// etc).

    This would generally only be needed for privately issued, or self-signed,
    certificates.

*   `ssl`: (Deprecated) This is a boolean value indicating whether SSL/TLS
    should be enabled. It was not consistently available across database
    connector types. It is the equivalent of `ssl_mode=require` and should no
    longer be used. It has been retained (for now) for backward compatibility.

*   `ca_cert`: (Deprecated) This is an alias for `ssl_ca_file`. It, too, was not
    consistently available across database connector types and should no longer
    be used. Use `ssl_ca_file` instead.


### Database Client Application Identification { data-toc-label="Client Identification" }

Some database types support a mechanism for the client to identify itself when
connecting, in addition to the user authentication. This information may then be
available in things such as connection logs, activity logs etc. The mechanism
used is database dependent and not all databases provide a mechanism.

Lava attempts to provide a uniform interface to the underlying database client
identification mechanism where possible.

For most of the built in database related job types, lava will automatically
provide a client identifier when connecting. By default, this is in the form
`lv-<REALM>-<JOB-ID>`. (See the `CONN_APP_NAME` [worker configuration
parameter](#general-configuration-parameters).)

Support in [sqlc](#job-type-sqlc) jobs is dependent on the capabilities of the
database specific CLI tool used to support the connection. Likewise for
executable job types (e.g. [exe](#job-type-exe) and [pkg](#job-type-pkg)) using
a CLI based connector. See also
[Connection Handling for Executable Jobs](#connection-handling-for-executable-jobs).

When using the lava API `get_pysql_connection()`, a new, optional
`application_name` parameter is available. If a value is not provided, a value
in the form described above is used *if* the lava job ID can be determined from
the presence of a `LAVA_JOB_ID` environment variable. This should work whenever
the API is being used within a lava job. See also
[Connection Handling for Python Based Jobs](#connection-handling-for-python-based-jobs).

In short, in most normal usage patterns for databases for which lava supports
client identification, it will, more or less, do the *right* thing without
modifying jobs or additional configuration.

Lava's support for a client identification mechanism is summarised in the
following table:

|       Job / Connection Type       | [MS SQL](#client-application-identification-for-sql-server-ms-sql) | [MySQL](#client-application-identification-for-mysql) | [Oracle](#client-application-identification-for-oracle) | [Postgres](#client-application-identification-for-postgres) | [Redshift](#client-application-identification-for-redshift) |
|-----------------------|--------|-------|--------|----------|----------|
| [sql](#job-type-sql)  | Yes    | Yes   | Yes | Yes      | Yes      |
| [sqli](#job-type-sqli)| Yes    | Yes   | Yes | Yes      | Yes      |
| [sqlc](#job-type-sqlc)|        |       |        | Yes      | Yes      |
| [sqlv](#job-type-sqlv)| Yes    | Yes   | Yes | Yes      | Yes      |
| [db_from_s3](#job-type-db_from_s3)| Yes    | Yes   | Yes | Yes      | Yes      |
| [redshift_unload](#job-type-redshift_unload)|        |       |        |          | Yes      |
| [lava-sql CLI](#lava-sql-utility) | (1)    | (1)   | (1) | (1)      | (1)      |
| [Lava API](#connection-handling-for-python-based-jobs) | (2)    | (2)   | (2) | (2)      | (2)      |

Notes:

1.  The **lava-sql** utility will automatically populate a client connection
    identifier when used as part of a lava job payload. In other usages, the
    `-a` / `--app-name` argument will need to be specified.

2.  The `get_pysql_connection()` API will automatically populate a client
    connection identifier when used as part of a lava job payload. In other
    usages, the otherwise optional `application_name` parameter will need to be
    specified.

!!! note
    This article by Andy Grunwald was very helpful when implementing database
    client identification in lava: your [database connection deserves a
    name](https://andygrunwald.com/blog/your-database-connection-deserves-a-name)

#### Client Application Identification for Postgres

Postgres flavoured databases use the `application_name` connection parameter to
identify client connections. Postgres will truncate the supplied value to 63
characters.

The following sample query will display connected application names.

```sql
SELECT usename, application_name, client_addr, backend_type
FROM pg_stat_activity;
```

#### Client Application Identification for Redshift

Redshift, like Postgres, uses the `application_name` connection parameter to
identify client connections. Redshift allows application names up to 250
characters.

The following sample query can display application names:

```sql
SELECT RTRIM(username)         AS user,
       sessionid,
       SUBSTRING(event, 1, 20) AS event,
       recordtime,
       RTRIM(authmethod)       AS auth,
       RTRIM(sslversion)       AS ssl,
       RTRIM(application_name) AS app_name
FROM stl_connection_log
ORDER BY recordtime DESC;
```

#### Client Application Identification for MySQL

MySQL use the `program_name` connection parameter to identify client
connections.

The performance schema must be enabled to run queries that access the
`program_name` parameter. For AWS Aurora instances, see
[Turning on the Performance Schema for Performance Insights on Aurora MySQL](https://docs.aws.amazon.com/AmazonRDS/latest/AuroraUserGuide/USER_PerfInsights.EnableMySQL.html)
for information on enabling the performance schema.

The following sample query, when run as an admin user, shows currently active
connections:

```sql
SELECT
 session_connect_attrs.ATTR_VALUE AS program_name,
 processlist.*
FROM information_schema.processlist
LEFT JOIN  performance_schema.session_connect_attrs ON (
 processlist.ID = session_connect_attrs.PROCESSLIST_ID
 AND session_connect_attrs.ATTR_NAME = "program_name"
)
```

The following query shows active connections for the current user:

```sql
SELECT
 session_account_connect_attrs.ATTR_VALUE AS program_name,
 processlist.*
FROM information_schema.processlist
LEFT JOIN  performance_schema.session_account_connect_attrs ON (
 processlist.ID = session_account_connect_attrs.PROCESSLIST_ID
 AND session_account_connect_attrs.ATTR_NAME = "program_name";
```

#### Client Application Identification for SQL Server (MS SQL)

SQL Server uses the `program_name` connection parameter to identify client
connections.

The following sample query, when run as an admin user, shows currently active
connections:

```sql
SELECT hostname, program_name, loginame, cmd
FROM sys.sysprocesses
WHERE loginame != 'rdsa';
```

#### Client Application Identification for Oracle

!!! note
    New in v8.3 (Mauna Loa).

Oracle provides the
[DBMS_APPLICATION_INFO](https://docs.oracle.com/en/database/oracle/oracle-database/26/arpls/DBMS_APPLICATION_INFO.html)
and
[DBMS_SESSION](https://docs.oracle.com/en/database/oracle/oracle-database/26/arpls/DBMS_SESSION.html)
packages to assist with client identification and tracing. These include the
following parameters:

| Parameter         | Description                                                  | Lava Usage                                                   |
| ----------------- | ------------------------------------------------------------ | ------------------------------------------------------------ |
| ACTION            | The current action within the module (max 32 bytes).         | Not used.                                                    |
| CLIENT_INFO       | An arbitrary string identifying the client (max 64 bytes).   | Set to the lava version and [python-oracledb](https://oracle.github.io/python-oracledb/) version. |
| CLIENT_IDENTIFIER | Case-sensitive application-specific identifier for the current database session (max 64 bytes). | Set to the lava provided client identifier.                  |
| MODULE            | The module/application name (max 48 bytes).                  | Set to `lava`.                                               |

!!! note
    The descriptions above are indicative. These parameters are primarily for
    user interpretation and naming is a bit arbitrary.

DBAs can use these parameter values to query activity tables / views such as
`V$SESSION`.

Within a session, the current settings for these parameters can be obtained thus:

```sql
SELECT
    SYS_CONTEXT('USERENV', 'MODULE')            AS module,
    SYS_CONTEXT('USERENV', 'ACTION')            AS action,
    SYS_CONTEXT('USERENV', 'CLIENT_INFO')       AS client_info,
    SYS_CONTEXT('USERENV', 'CLIENT_IDENTIFIER') AS client_identifier
FROM dual;
```

