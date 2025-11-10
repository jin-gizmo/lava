
## Job type: cmd

The **cmd** job type runs a single Linux command.

### Payload

The payload is the command string. This will be parsed using standard Linux
shell lexical analysis to determine the executable and arguments. Additional
arguments can also be specified with the `args` parameter.

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
|LAVA_S3_TMP|The private S3 temporary area for this job run. The command is allowed to put data here.|
|LAVA_WORKER|The worker name.|

### Parameters

|Parameter|Type|Required|Description|
|-|-|-|-------------------------------------------------------------|
|args|List[String]|No|A list of additional arguments for the command.|
|env|Map[String,String]|No|A map of additional environment variables for the command.|
|jinja|Boolean|No|If `false`, disable Jinja rendering of the payload. Default `true`.|
|timeout|String|No|By default, **cmd** jobs are killed after 10 minutes. This parameter can override that with values in the form `nnX` where `nn` is a number and `X` is `s` (seconds), `m` (minutes) or `h` (hours). Note that this must be less than the visibility timeout on the worker SQS queue.|
|vars|Map[String,\*]|No|A map of variables injected when the command arguments and environment are Jinja rendered.|

### Jinja Rendering of the Payload and Environment

The collected arguments for the command and any environment values defined in
the job specification are individually rendered using
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

### Dev Mode Behaviour

Normally, the **cmd** job will copy stdout and stderr to S3 on the conclusion
of the job. In dev mode, stdout and stderr are emitted locally during the job
run instead of being copied to S3.

### Examples

The following example will list the contents of the S3 payloads area for this
realm.

```json
{
  "description": "List S3",
  "dispatcher": "Sydney",
  "enabled": true,
  "job_id": "demo/list_s3",
  "owner": "demo@somewhere.com",
  "payload": "aws s3 ls {{realm.s3_payloads}}/ --recursive",
  "type": "cmd",
  "worker": "default"
}
```

This does the same thing but with the arguments supplied a little differently.


```json
{
  "description": "List S3",
  "dispatcher": "Sydney",
  "enabled": true,
  "job_id": "demo/list_s3",
  "owner": "demo@somewhere.com",
  "parameters": {
    "args": [
      "--recursive"
    ]
  },
  "payload": "aws s3 ls {{realm.s3_payloads}}/",
  "type": "cmd",
  "worker": "default"
}
```

