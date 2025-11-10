
## Job type: exe

The **exe** job type downloads one or more executables from the S3 payload area
and runs them.

### Payload

The payload is a location in S3 relative to the `s3_payloads` area specified in
the [realms table](#the-realms-table). It can be either an
object key, in which case a single executable is downloaded, or a prefix ending
in `/`, in which case all executables under that prefix will be downloaded and
run in lexicographic order.

See [S3 Payloads](#s3-payloads) for more information.

The payload value will be parsed using standard Linux shell lexical analysis to
determine the S3 object location and, optionally, any arguments. Additional
arguments can also be specified with the `args` parameter.

!!! info
    The `exe` job type requires the payload to be a single string. It does not
    support the list mechanism provided by the
    [v2 Payload Downloader](#the-v2-payload-downloader).

### Environment

Stdin will be redirected from `/dev/null`. Stdout and stderr are captured and,
if non-empty, placed into the realm `s3_temp` area with the following
prefixes:

*   stdout: `<s3_temp>/<job_id>/<run_id>/stdout`

*   stderr: `<s3_temp>/<job_id>/<run_id>/stderr`

The following variables are placed into the environment for the command.

|Variable|Description|
|-|-------------------------------------------------------------|
|LAVA_JOB_ID|The `job_id`.|
|LAVA_OWNER|The value of the `owner` field from the job specification.|
|LAVA_REALM|The realm name.|
|LAVA_RUN_ID|The `run_id` UUID.|
|LAVA_S3_KEY|The identifier for the KMS key needed to write data into the S3 temporary area.|
|LAVA_S3_PAYLOAD|The payload location for this job.|
|LAVA_S3_TMP|The private S3 temporary area for this job run. The executables are allowed to put data here.|
|LAVA_WORKER|The worker name.|
|PYTHONPATH|The PYTHONPATH has the lava code directory appended. This allows Python based executables to directly import lava modules. This is particularly handy for accessing the lava connection manager from within a Python program.|

!!! warning
    If the payload is a script (e.g. bash or Python) then Lava relies on the
    hashbang line at the beginning of the file. If the file has been edited on a
    DOS system then it may have DOS style CR-LF line endings which will cause
    the script interpreter to be unrecognised and the job will fail.

### Parameters

|Parameter|Type|Required|Description|
|-|-|-|-------------------------------------------------------------|
|args|List[String]|No|A list of additional arguments for the executable(s).|
|connections|Map[String,String]|No|A dictionary with keys that are connection labels and the values are conn_id|
|env|Map[String,String]|No|A map of additional environment variables for the command.|
|jinja|Boolean|No|If `false`, disable Jinja rendering of the `args`. Default `true`.|
|timeout|String|No|By default, executables run by **exe** jobs are killed after 10 minutes. This parameter can override that with values in the form `nnX` where `nn` is a number and `X` is `s` (seconds), `m` (minutes) or `h` (hours). Note that the total timeout for the entire job (`timeout` multiplied by number of payload elements) must be less than the visibility timeout on the worker SQS queue.|
|vars|Map[String,\*]|No|A map of variables injected when the command arguments and environment are Jinja rendered.|

### Jinja Rendering of the Arguments and Environment

The collected arguments for the executable(s) and any environment values defined
in the job specification are individually rendered using
[Jinja](http://jinja.pocoo.org) prior to execution.

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

### Connection Handling

Lava provides a mechanism for **exe** jobs to utilise connections defined in the
[connections table](#the-connections-table). It does this by
creating a small executable that gives effect to the connection and then placing
the name of that executable into an environment variable where it can be
accessed by the job payload.

For example, consider a `parameters` field for the job like the following,

```json
{
  "parameters": {
    "connections": {
      "pgres_db": "conn_id_for_postgres"
    }
  }
}
```

Lava will create a small executable that automates connection to the relevant
Postgres database using the Postgres command line client (psql) and place the
name of that executable in the environment variable `LAVA_CONN_PGRES_DB`. A
second environment variable, `LAVA_CONNID_PGRESS_DB` will contain the connection
ID itself, `conn_id_for_postgres` in this case.

If the payload is a shell script, for example, it would use this in the
following way:

```bash
# Use $LAVA_CONN_PGRES_DB anywhere you could use the psql CLI.
# The authentication is automated behind the scenes.

$LAVA_CONN_PGRES_DB <<!
SELECT * FROM pg_user
WHERE usename = 'fred';
!
```

If the payload is a Python script, the lava connection manager can be used
directly to provide a native Python DBAPI 2.0 connection object, thus:

```python
import os
from lava.connection import get_pysql_connection

conn = get_pysql_connection(
    conn_id=os.environ['LAVA_CONNID_PGRESS_DB'],
    realm=os.environ['LAVA_REALM']
)

# Now use conn object in the usual way.
```

All of the database connectors work in the same way. Non-database connectors have
a similar interface but the behaviour and usage depends on the underlying nature
of the thing to which connection is required.

### Dev Mode Behaviour

Normally, the **exe** job will copy stdout and stderr to S3 on the conclusion
of the job. In dev mode, stdout and stderr are emitted locally during the job
run instead of being copied to S3.

### Examples

The following example will download and run a shell script with a non-standard
timeout of 20 minutes.

```json
{
  "description": "Test pgconnector from exe",
  "dispatcher": "Sydney",
  "enabled": true,
  "job_id": "demo/shell",
  "owner": "demo@somewhere.com",
  "parameters": {
    "timeout": "20m"
  },
  "payload": "demo/shell_script.sh",
  "type": "exe",
  "worker": "default"
}
```

This one will download all files under the `demo/scripts/` prefix
from the payloads area and run them. Note that the download is not recursive.

```json
{
  "description": "Test pgconnector from exe",
  "dispatcher": "Sydney",
  "enabled": true,
  "job_id": "demo/multi_exe",
  "owner": "demo@somewhere.com",
  "payload": "demo/scripts/",
  "type": "exe",
  "worker": "default"
}
```

This one will run a Python script and provide it with connection handles to a
Postgres database and a MySQL database. The command needed to run a Postgres
database client with auto-connect will be in the environment variable
`LAVA_CONN_PGRES_DB`. The command needed to run a MySQL database client with
auto-connect will be in the environment variable `LAVA_CONN_MYSQL_DB`.

```json
{
  "description": "Run pgconnector from exe",
  "dispatcher": "Sydney",
  "enabled": true,
  "job_id": "demo/py_exe",
  "owner": "demo@somewhere.com",
  "parameters": {
    "connections": {
      "mysql_db": "conn_id_for_mysql",
      "pgres_db": "conn_id_for_postgres"
    }
  },
  "payload": "demo/conect_to_db.py",
  "type": "exe",
  "worker": "default"
}
```

This one will run an executable with some arguments.


```json
{
  "description": "How to pass arguments to the exe",
  "dispatcher": "Sydney",
  "enabled": true,
  "job_id": "demo/exe_with_args",
  "owner": "demo@somewhere.com",
  "payload": "demo/my-exe -y --log-level info",
  "type": "exe",
  "worker": "default"
}
```

This one will do exactly the same thing with the arguments specified in a
different way.


```json
{
  "description": "How to pass arguments to the exe",
  "dispatcher": "Sydney",
  "enabled": true,
  "job_id": "demo/exe_with_args",
  "owner": "demo@somewhere.com",
  "payload": "demo/my-exe -y",
  "parameters": {
    "args": [
      "--log-level",
      "info"
    ]
  },
  "type": "exe",
  "worker": "default"
}
```

And again.

```json
{
  "description": "How to pass arguments to the exe",
  "dispatcher": "Sydney",
  "enabled": true,
  "job_id": "demo/exe_with_args",
  "owner": "demo@somewhere.com",
  "payload": "demo/my-exe -y --log-level {{vars.level}}",
  "parameters": {
    "vars": {
      "level": "info"
    }
  },
  "type": "exe",
  "worker": "default"
}
```
