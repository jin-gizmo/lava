
## Job type: sqlv

The **sqlv** job type runs one or more files containing SQL statements. It is
essentially a hybrid of the [sql](#job-type-sql) and
[sqlc](#job-type-sqlc) job types. It has a consistent, lava
controlled interface across all database types like the former, but uses an
external CLI client like the latter.

!!! tip
    For help selecting the appropriate SQL job type, see
    [Choosing an SQL Job Type](#choosing-an-sql-job-type).

The client, `lava-sql` is provided as part of the lava code base. It supports
SQL statements only, not the meta-commands that are typical of the proprietary
database clients used by [sqlc](#job-type-sqlc). The
[lava-sql](#lava-commands-and-utilities)
utility can also be used stand-alone or invoked by lava
[exe](#job-type-exe), [pkg](#job-type-pkg) and
[docker](#job-type-docker) jobs.

Connection to the target database is handled automatically by lava.

### Payload

The payload is a location in S3 relative to the `s3_payloads` area specified in
the [realms table](#the-realms-table). It can be either an object
key, in which case a single file is downloaded, or a prefix ending in /, in
which case all files under that prefix will be downloaded and run in
lexicographic order.


See [S3 Payloads](#s3-payloads) for more information.

!!! note
    The `sqlv` job type also allows the payload to be a list of S3 locations if the
    [v2 Payload Downloader](#the-v2-payload-downloader) is enabled.

Each payload file can contain one or more SQL statements that are compatible
with the target database.

For `SELECT` statements, the output is placed in its own file in the `s3_temp`
area. Unless modified by job parameters, the output of each `SELECT` statement
is pipe separated values, one record per line.

!!! tip
    All output is placed in a single file. To avoid a mess, each job should
    either limit itself to a single `SELECT` statement that produces output or
    all `SELECT` statements should produce the same column structure.

### Parameters

Some of the formatting related parameters are output format dependent. In most
cases, defaults can be overridden at the realm level using
[configuration variables](#configuration-for-sql-sqli-and-sqlv-jobs).

|Parameter|Type|Required|Description|
|-|-|-|-------------------------------------------------------------|
|batch_size|Integer|No|Fetch this many rows at a time. Default is 1000.|
|conn_id|String|Yes|The [connection ID](#database-connectors) for an SQL database.|
|delimiter|String|No|Single character field delimiter. Default `|`.|
|dialect|String|No|As for [csv.writer](https://docs.python.org/library/csv.html#csv-fmt-params). Default `excel`. The `unix` option is useful when DOS style line endings must be avoided.|
|doublequote|Boolean|No|As for [csv.writer](https://docs.python.org/library/csv.html#csv-fmt-params). Default `false`.|
|escapechar|String|No|As for [csv.writer](https://docs.python.org/library/csv.html#csv-fmt-params). Default `null`.|
|format|String|No|Specify the output format for `SELECT` statements. Any of the formats supported by the [lava-sql](#lava-sql-utility) can be used. The default is `csv`.|
|jinja|Boolean|No|If `false`, disable Jinja rendering of the payload. Default `true`.|
|header|Boolean|No|Add a header for data produced from SELECT queries. Default is `false`.|
|level|String|No|Print log messages of a given severity level or above. The standard logging level names are available but `debug`, `info`, `warning` and `error` are most useful. The Default is `info`.|
|quotechar|String|No|As for [csv.writer](https://docs.python.org/library/csv.html#csv-fmt-params). Default `"`.|
|quoting|String|No|As for [csv.writer](https://docs.python.org/library/csv.html#csv-fmt-params) `QUOTE_*` parameters (without the QUOTE_ prefix). Default `minimal` (i.e. `QUOTE_MINIMAL`).|
|raw|Boolean|No|By default, an attempt will be made to split each payload file into individual SQL statements. This should be safe in most cases. To suppress this behaviour and run the payload as-is, set raw to `true`. Default `false`.|
|timeout|String|No|By default, jobs are killed after 10 minutes. This parameter can override that with values in the form `nnX` where `nn` is a number and `X` is `s` (seconds), `m` (minutes) or `h` (hours). Note that the total timeout for the entire job (`timeout` multiplied by number of payload elements) must be less than the visibility timeout on the worker SQS queue.|
|transaction|Boolean|No|If `true`, auto-commit is disabled and the sequence of SQLs is run within a transaction. If `false`, auto-commit is enabled (if supported by the driver). Default `false`.|
|vars|Map[String,*]|No|A map of variables injected when the SQL is Jinja rendered.|

### Jinja Rendering of the Payload

Each SQL statement is rendered using [Jinja](http://jinja.pocoo.org) prior to
execution.

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
|realm|dict[str,*]|The realm specification.|
|start|datetime|The local time when the job run started.|
|state|dict[str,\*]|A dictionary of the state items imported into the job, keyed on state_id. The default values are updated at run-time with any current values obtainable from the [state](#the-state-table) table.|
|ustart|datetime|The UTC time when the job run started.|
|utils|dict[str,runnable]|A dictionary of [utility functions](#jinja-utility-functions) that can be used in the Jinja markup.|
|vars|dict[str,\*]|A dictionary of variables provided as the `vars` component of the job `parameters`.|

### Dev Mode Behaviour

Normally, the **sqlv** job will copy stdout and stderr to S3 on the conclusion
of the job. In dev mode, stderr is emitted locally during the job
run instead of being copied to S3. Stdout will still be copied to S3 as it may
contain binary information.

### Examples

The following example runs the SQL statements in `demo/query-mytable.sql`. The
output is written to `demo/query-mytable.sql.out` in the `s3_temp` area.

```json
{
  "description": "Run a file containing SQL statements.",
  "dispatcher": "Sydney",
  "enabled": true,
  "job_id": "demo/sql-query-01",
  "owner": "demo@somewhere.com",
  "parameters": {
    "conn_id": "db-conn-01",
    "delimiter": "|",
    "quoting": "all",
    "timeout": "20m",
    "transaction": true
  },
  "payload": "demo/queries.sql",
  "type": "sqlc",
  "worker": "default"
}
```
