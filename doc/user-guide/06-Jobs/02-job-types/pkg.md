
## Job type: pkg

The **pkg** job type downloads one or more code packages from the S3 payload
area, unpacks them and runs the nominated executable within the package using
the same invocation mechanism as the [exe job
type](#job-type-exe).

Supported package types are:

*   Tar files, including any compressed variants supported by the standard Linux
    tar command.

*   Zip files.

### Payload

The payload is a location in S3 relative to the `s3_payloads` area specified
in the [realms table](#the-realms-table). It can be either an object
key, in which case a single package is downloaded, or a prefix ending in `/`,
in which case all packages under that prefix will be downloaded and run in
lexicographic order.

See [S3 Payloads](#s3-payloads) for more information.

!!! note
    The `pkg` job type also allows the payload to be a list of S3 locations if
    the [v2 Payload Downloader](#the-v2-payload-downloader) is enabled.

### Environment

Stdin will be redirected from `/dev/null`. Stdout and Stderr are captured and,
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

!!! warning Beware DOS
    If the entry point in the payload is a script (e.g. bash or Python) then
    Lava relies on the hashbang line at the beginning of the file. If the file
    has been edited on a DOS system then it may have DOS style CR-LF line
    endings which will cause the script interpreter to be unrecognised and the
    job will fail.


### Parameters

|Parameter|Type|Required|Description|
|-|-|-|-------------------------------------------------------------|
|args|List[String]|No|A list of additional arguments for the main executable(s).|
|command|String|Yes|The name of the entry point executable in the bundle, relative to the root of the bundle. This will be parsed using standard Linux shell lexical analysis to determine the executable and arguments. Additional arguments can also be specified with the `args` parameter.|
|connections|Map[String,String]|No|A dictionary with keys that are connection labels and the values are conn_id|
|env|Map[String,String]|No|A map of additional environment variables for the command.|
|jinja|Boolean|No|If `false`, disable Jinja rendering of the `args`. Default `true`.|
|timeout|String|No|By default, executables run by **exe** jobs are killed after 10 minutes. This parameter can override that with values in the form `nnX` where `nn` is a number and `X` is `s` (seconds), `m` (minutes) or `h` (hours). Note that the total timeout for the entire job (`timeout` multiplied by number of payload elements) must be less than the visibility timeout on the worker SQS queue.|
|vars|Map[String,\*]|No|A map of variables injected when the arguments and environment are Jinja rendered.|

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

Connections are handled exactly as for the [exe job
type](#job-type-exe).

### Dev Mode Behaviour

Normally, the **pkg** job will copy stdout and stderr to S3 on the conclusion
of the job. In dev mode, stdout and stderr are emitted locally during the job
run instead of being copied to S3.

### Examples

The following example will download a zip file, unpack it and run the main
executable:

```json
{
  "description": "Run a package of code.",
  "dispatcher": "Sydney",
  "enabled": true,
  "job_id": "demo/my-pkg",
  "owner": "demo@somewhere.com",
  "parameters": {
    "command": "main-script.sh --log-level warning"
  },
  "payload": "demo/my-pkg.zip",
  "type": "pkg",
  "worker": "default"
}
```
