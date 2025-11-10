
## Job type: dispatch

The **dispatch** job type initiates a dispatch of other jobs.

Unlike the [chain job type](#job-type-chain), this is an
asynchronous operation in that the dispatch is initiated but the job run does
not wait for the dispatched jobs to actually start. The dispatched jobs will not
necessarily run on the same worker and will each have their own `run_id`.

Any globals available in the **dispatch** job will also be passed in the
dispatch requests to the jobs being dispatched.

### Payload

The payload is a comma separated list, or an actual list of job IDs to dispatch.

### Parameters

|Parameter|Type|Required|Description|
|-|-|-|-------------------------------------------------------------|
|delay|String|No|Dispatch message sending delay in the form `nnX` where `nn` is a number and `X` is `s` (seconds) or `m` (minutes). The maximum allowed value is 15 minutes.|
|jinja|Boolean|No|If `false`, disable Jinja rendering of the payload. Default `true`.|
|job\_prefix|String|No|Prepend the specified value to each job ID in the payload.|
|parameters|Map[String,\*]|No|A map of parameters that will be passed to the job being dispatched. This is Jinja rendered.|

### Handling of Globals

The **dispatch** job type merges its globals into those of the child jobs being
dispatched. A value specified in the parent **dispatch** job will override a
similarly named value in the child.

In addition, the **dispatch** job will also add
[lava specific globals](#globals-owned-by-lava) under
`globals.lava`. These lava owned globals allow all jobs dispatched as a result
of the current job to access some common global values.

### Jinja Rendering of the Payload

The `parameters` parameter is Jinja rendered.

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

### Dev Mode Behaviour

The **dispatch** job behaviour is unchanged for dev mode.

### Examples

The following example dispatches two downstream jobs with no delay.

```json
{
  "description": "Dispatch two downstream jobs",
  "dispatcher": "Sydney",
  "enabled": true,
  "job_id": "demo/dispatch2",
  "owner": "demo@somewhere.com",
  "payload": "demo/job_01, demo/job_02",
  "type": "dispatch",
  "worker": "default"
}
```

This one dispatches a downstream job with a 5 minute delay and some additional
parameters being passed to the dispatched job. Jinja rendering is disabled.

```json
{
  "description": "Dispatch a downstream job",
  "dispatcher": "Sydney",
  "enabled": true,
  "job_id": "demo/dispatch1",
  "owner": "demo@somewhere.com",
  "payload": "demo/job_01, demo/job_02",
  "parameters": {
    "delay": "5m",
    "jinja": false,
    "parameters": {
      "param01": "Hello",
      "param02": "world"
    }
  },
  "type": "dispatch",
  "worker": "default"
}
```
