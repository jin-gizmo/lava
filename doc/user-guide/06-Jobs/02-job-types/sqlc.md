
## Job type: sqlc

The **sqlc** job type runs one or more files containing native SQL client
commands. It differs from the [sql](#job-type-sql) and
[sqli](#job-type-sqli) job types in that, instead of a Python
DBAPI 2.0 driver, it uses a command line client specific to the target database
type. This makes **sqlc** less portable than
[sql](#job-type-sql)/[sqli](#job-type-sqli)/[sqlv](#job-type-sqlv) as
the former allows access to all the meta-commands available in the command line
client.

The **sqlc** job type is intended for more complex requirements where the
specific capabilities of the native CLI are critical. In most cases, one of the
[sql](#job-type-sql), [sqli](#job-type-sqli) or [sqlv](#job-type-sqlv) job types
will be more appropriate.

!!! tip
    For help selecting the appropriate SQL job type, See
    [Choosing an SQL Job Type](#choosing-an-sql-job-type).


The stdout and stderr of each SQL script, if any, is placed in its own file in
the `s3_temp` area.

For Postgres flavoured databases (including Redshift), the
[psql](https://www.postgresql.org/docs/9.6/reference-client.html) client is
used. For MySQL databases, the
[mysql](https://dev.mysql.com/doc/refman/8.0/en/mysql.html) client is used.
For Oracle databases, the SQL\*Plus client is used. It's a horror. Sorry.

### Payload

The payload is a location in S3 relative to the `s3_payloads` area specified in
the [realms table](#the-realms-table). It can be either an object
key, in which case a single file is downloaded, or a prefix ending in /, in
which case all files under that prefix will be downloaded and run in
lexicographic order.

See [S3 Payloads](#s3-payloads) for more information.

!!! note
    The `sqlc` job type also allows the payload to be a list of S3 locations if the
    [v2 Payload Downloader](#the-v2-payload-downloader) is enabled.

Each file may contain a mix of SQL statements and client
meta-commands. The SQL must be compatible with the target database. SQL
commands must always be properly terminated with semi-colons.

### Parameters

|Parameter|Type|Required|Description|
|-|-|-|-------------------------------------------------------------|
|args|List[String]|No| A list of zero or more additional arguments provided to the database client. These are necessarily specific to the database type and underlying database client.|
|conn\_id|String|Yes|The connection ID for a database.|
|jinja|Boolean|No|If `false`, disable Jinja rendering of the payload. Default `true`.|
|timeout|String|No|By default, payload components run by **sqlc** jobs are killed after 10 minutes. This parameter can override that with values in the form `nnX` where `nn` is a number and `X` is `s` (seconds), `m` (minutes) or `h` (hours). Note that the total timeout for the entire job (`timeout` multiplied by number of payload elements) must be less than the visibility timeout on the worker SQS queue.|
|vars|Map[String,\*]|No|A map of variables injected when the SQL is Jinja rendered.|

### Jinja Rendering of the Payload

Each file in the payload is rendered using [Jinja](http://jinja.pocoo.org)
prior to execution.

All of the injected parameters are effectively Python objects so the normal
Jinja syntax and Python methods for those objects can be used in the Jinja
templates. This is particularly useful for the
[datetime](https://docs.python.org/3/library/datetime.html#datetime-objects)
objects as `strftime()` becomes available. For example, the S3 location of
the unload (`s3key`) can be dynamically set to include components such as the
schema, table name, unload date etc.

Refer to [Jinja Rendering in Lava](#jinja-rendering-in-lava)
for more information.

The following variables are made available to the renderer.

|Name|Type|Description|
|-|-|-------------------------------------------------------------|
|globals|dict[str,\*]|The `globals` from the job specification updated with any globals received in the job dispatch.|
|job|dict[str,\*]|The [augmented job specification](#the-augmented-job-specification).|
|realm|dict[str,\*]|The realm specification.|
|start|datetime|The local time when the job run started.|
|state|dict[str,\*]|A dictionary of the state items imported into the job, keyed on state_id. The default values are updated at run-time with any current values obtainable from the [state](#the-state-table) table.|
|ustart|datetime|The UTC time when the job run started.|
|utils|dict[str,runnable]|A dictionary of [utility functions](#jinja-utility-functions) that can be used in the Jinja markup.|
|vars|dict[str,\*]|A dictionary of variables provided as the `vars` component of the job `parameters`.|

### Dev Mode Behaviour

Normally, the **sqlc** job will copy stdout and stderr to S3 on the conclusion
of the job. In dev mode, stdout and stderr are emitted locally during the job
run instead of being copied to S3.

### Examples

The following example runs all of the commands in `demo/psql-commands.sql`. The
`--no-align` argument is passed to the `psql` command line client. Stdout is
written to `demo/sqlc-query-01.sql.stdout` and stderr is written to
`demo/sqlc-query-01.sql.sterr` in the `s3_temp` area. The underlying database
type is specified in the connection specification not the job specification but
the payload must match the underlying database type.


```json
{
  "description": "Run a psql file.",
  "dispatcher": "Sydney",
  "enabled": true,
  "job_id": "demo/sqlc-query-01",
  "owner": "demo@somewhere.com",
  "parameters": {
    "args": [
      "--no-align"
    ],
    "conn_id": "pgdb-conn-01"
  },
  "payload": "demo/psql-commands.sql",
  "type": "sql",
  "worker": "default"
}
```

This one runs all files found under the given payload prefix. Separate stdout
and stderr files are created for each payload file. The timeout for each
individual payload element is set to 30 minutes.

```json
{
  "description": "Run a psql file.",
  "dispatcher": "Sydney",
  "enabled": true,
  "job_id": "demo/sqlc-query-01",
  "owner": "demo@somewhere.com",
  "parameters": {
    "args": [
      "--no-align"
    ],
    "conn_id": "pgdb-conn-01"
  },
  "payload": "demo/psql-commands/",
  "timeout": "30m",
  "type": "sql",
  "worker": "default"
}
```
