
## Job type: sqli

The **sqli** job type runs one or more SQL statements.

The **sqli** job type is functionally identical to the
[sql](#job-type-sql) job type with the exception that **sqli**
obtains the SQL statements inline from the payload whereas for
[sql](#job-type-sql) jobs the payload specifies S3 objects
containing the SQL statements.

!!! tip
    For help selecting the appropriate SQL job type, see
    [Choosing an SQL Job Type](#choosing-an-sql-job-type).

Connection to the target database is handled automatically by lava.

The **sqli** job type is intended for simple, relatively small SQL sequences.
For larger or more complex cases, the [sql](#job-type-sql) or
[sqlc](#job-type-sqlc) job types may be more appropriate.

### Payload

The payload is a string, or list of strings, containing SQL statements.

Each payload string can itself contain one or more SQL statements that are
compatible with the target database.

For statements that produce result tuples (e.g. `SELECT` statements), the output
is placed in its own file in the `s3_temp` area. Unless modified by job
parameters, the output of each statement is pipe separated values, one
record per line.

Note that some database drivers are pickier than others about the presence or
absence of a terminating semi-colon (e.g. Oracle) so these will be stripped
from the end of each statement before execution.

### Parameters

Parameters are identical to those for the [sql](#job-type-sql)
job type.

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

Files are named `<m>.<n>.out`, where:

*   `<m>` is the sequence number of the payload element, starting from zero. 
    Note that each payload element can contain multiple SQL statements.
    Hence ...
*   `<n>` is the SQL statement sequence number within the payload element,
    starting from zero.

So, with an `output` parameter of `whatever` and a payload list containing a
single element which is a `SELECT` statement, the output file would be named
`whatever/0.0.out`.

As child jobs in [chain](#job-type-chain) and [dag](#job-type-dag) jobs all
share the same run directory, this provides a mechanism for one child job to
leave data behind for a subsequent job.

!!! info
    It is **critical** to use the `output` parameter in these circumstances.

Unless modified by job parameters, the output of each `SELECT` statement is pipe
separated values, one record per line.


### Jinja Rendering of the Payload

Each SQL statement is rendered using [Jinja](http://jinja.pocoo.org) prior to
execution. The rendering process is identical to that for the
[sql](#job-type-sql) job type.

### Dev Mode Behaviour

The **sqli** job behaviour is unchanged for dev mode.

### Examples

The following example runs a single SQL statement.
The output is written to the `s3_temp` area.

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
  "payload": "SELECT numbers FROM lottery_results WHERE result_date > NOW()",
  "type": "sqli",
  "worker": "default"
}
```

The following example runs multiple SQL statements in a transaction.

```json
{
  "description": "Run multiple SQL statements.",
  "dispatcher": "Sydney",
  "enabled": true,
  "job_id": "demo/sql-query-01",
  "owner": "demo@somewhere.com",
  "parameters": {
    "conn_id": "db-conn-01",
    "delimiter": "|",
    "quoting": "all",
    "transaction": true
  },
  "payload": [
    "DELETE FROM main_table",
    "INSERT INTO main_table (SELECT * FROM staging_table)"
  ],
  "type": "sqli",
  "worker": "default"
}
```
