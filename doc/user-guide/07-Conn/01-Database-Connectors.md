
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

### Database Authentication Using AWS SSM Parameter Store { data-toc-label="Authentication Using SSM Parameters" }

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

### Database Authentication Using AWS Secrets Manager { data-toc-label="Authentication Using Secrets Manager" }

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

### Database Authentication Using IAM Credential Generation { data-toc-label="Authentication Using IAM" }

Some AWS database types provide an IAM based mechanism for obtaining temporary
database credentials. Lava supports this mechanism for some connectors. The
mechanism will be used where the connection specification (after inclusion of
any AWS Secrets Manager components) does not contain a password.

Refer to individual connector details for more information.

### Database Client Application Identification { data-toc-label="Client Application Identification" }

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

|       Job Type        | MS SQL | MySQL | Oracle | Postgres | Redshift | SQLite |
|-----------------------|--------|-------|--------|----------|----------|--------|
| [sql](#job-type-sql)  | Yes    | Yes   |        | Yes      | Yes      |        |
| [sqli](#job-type-sqli)| Yes    | Yes   |        | Yes      | Yes      |        |
| [sqlc](#job-type-sqlc)|        |       |        | Yes      | Yes      |        |
| [sqlv](#job-type-sqlv)| Yes    | Yes   |        | Yes      | Yes      |        |
| [db_from_s3](#job-type-db_from_s3)| Yes    | Yes   |        | Yes      | Yes      |        |
| [redshift_unload](#job-type-redshift_unload)|        |       |        |          | Yes      |        |
| lava-sql CLI    | (1)    | (1)   |        | (1)      | (1)      |        |
| Lava API        | (2)    | (2)   |        | (2)      | (2)      |        |

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
