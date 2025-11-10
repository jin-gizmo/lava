
## Job type: sql

The **sql** job type runs one or more SQL statements.

The **sql** job type is functionally identically to the
[sqli](#job-type-sqli) job type with the exception that **sql**
obtains the SQL statements from files in S3 whereas for
[sqli](#job-type-sqli) jobs the payload is inline in the job
specification.

!!! tip
    For help selecting the appropriate SQL job type, See
    [Choosing an SQL Job Type](#choosing-an-sql-job-type).

Connection to the target database is handled automatically by lava.

The **sql** job type is intended for simple SQL sequences. For more complex
cases, the [sqlc](#job-type-sqlc) or
[sqlv](#job-type-sqlv) job types may be more appropriate.

### Payload

The payload is a location in S3 relative to the `s3_payloads` area specified in
the [realms table](#the-realms-table). It can be either an object
key, in which case a single file is downloaded, or a prefix ending in /, in
which case all files under that prefix will be downloaded and run in
lexicographic order.

See [S3 Payloads](#s3-payloads) for more information.

!!! info
    The `sql` job type also allows the payload to be a list of S3 locations if
    the [v2 Payload Downloader](#the-v2-payload-downloader) is enabled.

Each payload file can contain one or more SQL statements that are compatible
with the target database.

Note that some database drivers are pickier than others about the presence or
absence of a terminating semi-colon (e.g. Oracle) so these will be stripped
from the end of each statement before execution.

### Parameters

The formatting related parameters are as defined for the Python CSV writer,
although some of the defaults are different. Defaults can be overridden at the
realm level using [configuration
variables](#configuration-for-sql-sqli-and-sqlv-jobs).

|Parameter|Type|Required|Description|
|-|-|-|-------------------------------------------------------------|
|batch_size|Integer|No|Fetch this many rows at a time. Default is 1000.|
|conn_id|String|Yes|The [connection ID](#database-connectors) for an SQL database.|
|delimiter|String|No|Single character field delimiter. Default `|`.|
|dialect|String|No|As for [csv.writer](https://docs.python.org/library/csv.html#csv-fmt-params). Default `excel`. The `unix` option is useful when DOS style line endings must be avoided.|
|doublequote|Boolean|No|As for [csv.writer](https://docs.python.org/library/csv.html#csv-fmt-params). Default `false`.|
|escapechar|String|No|As for [csv.writer](https://docs.python.org/library/csv.html#csv-fmt-params). Default `null`.|
|header|Boolean|No|Add a header for data produced from SELECT queries. Default is `false`.|
|jinja|Boolean|No|If `false`, disable Jinja rendering of the payload. Default `true`.|
|output|String|No|If specified, the output from statements that produce result tuples will be placed in this subdirectory in both the job run temporary area in the local filesystem and in the `s3_temp` area. This option must be specified for [dag](#job-type-dag) jobs if the output is needed. See [Output Data](#output-data) below. It must contain only alphanumeric characters and underscores.|
|quotechar|String|No|As for [csv.writer](https://docs.python.org/library/csv.html#csv-fmt-params). Default `"`.|
|quoting|String|No|As for [csv.writer](https://docs.python.org/library/csv.html#csv-fmt-params) `QUOTE_*` parameters (without the QUOTE_ prefix). Default `minimal` (i.e. `QUOTE_MINIMAL`).|
|raw|Boolean|No|By default, an attempt will be made to split each payload file into individual SQL statements. This should be safe in most cases. To suppress this behaviour and run the payload as-is, set raw to `true`. Default `false`.|
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

### Output Data

If any of the queries in the payload produce result tuples (e.g. `SELECT`
statements), the output is placed in its own file in the local file system and
in the `s3_temp` area.

If the `output` parameter is not specified, the output files will be placed in
the root of the temporary run directory on the local worker file system and at
the root of the job run's `s3_temp` area.

If the `output` parameter is specified, the output files will be placed in a
subdirectory of that name under the root of the temporary run directory on the
local worker file system and under a similarly named sub-prefix of the root
of the job run's `s3_temp` area.

Files are named `<PAYLOAD>.<n>.out`, where:

*   `<PAYLOAD>` is the name of the payload file containing the `SELECT` query;
    and
*   `<n>` is the SQL statement sequence number within that file, starting from
    zero.

So with an `output` parameter of `whatever` and a payload file,
`some-queries.sql`, containing only a `SELECT` statement,
the output file would be named `whatever/some-queries.sql.0.out`.

As child jobs in [chain](#job-type-chain) and [dag](#job-type-dag) jobs all
share the same run directory, this provides a mechanism for one child job to
leave data behind for a subsequent job.

!!! info
    It is **critical** to use the `output` parameter in these circumstances.

Unless modified by job parameters, the output of each `SELECT` statement is pipe
separated values, one record per line.

### Dev Mode Behaviour

The **sql** job behaviour is unchanged for dev mode.

### Examples

The following example runs the SQL statement in `demo/query-mytable.sql`. The
output is written to `demo/query-mytable.sql.out` in the `s3_temp` area.

```json
{
  "description": "Run a single SQL statement.",
  "dispatcher": "Sydney",
  "enabled": true,
  "job_id": "demo/sql-query-01",
  "owner": "demo@somewhere.com",
  "parameters": {
    "conn_id": "db-conn-01",
    "delimiter": "|",
    "quoting": "all"
  },
  "payload": "demo/query-mytable.sql",
  "type": "sql",
  "worker": "default"
}
```
