
## Job type: lavasched

The **lavasched** job type is a special lava internal job type. It must be run
only on workers that are also [dispatchers](#dispatchers) for
the realm to create the crontab on that node to dispatch jobs.

Each crontab entry schedules the dispatch of a job by running `lava-dispatcher`
to send an SQS message to the appropriate worker SQS queue.

The **lavasched** jobs must themselves be scheduled to update the crontab
periodically to accommodate changes in the [jobs
table](#the-jobs-table). Refer to the section on [Scheduled
Dispatch](#scheduled-dispatch) for more information on how to
initialise this process.

Refer to the section [Schedule
Specifications](#schedule-specifications) for more information.

### Payload

The payload is ignored for **lavasched** jobs.

### Parameters

|Parameter|Type|Required|Description|
|-|-|-|-------------------------------------------------------------|
|args|List[String]|No|A list of additional arguments that will be added to the invocation of `lava-dispatcher` in the crontab entries.|
|dispatcher|String _or_ List[String]|Yes|Name of dispatcher, or a list of names, specifying the dispatchers for which schedules should be built.|
|env|Map[String,String]|No|A map of environment variables that will be added into the crontab. Of these, the most useful is `CRON_TZ`, which controls the timezone used by cron for this dispatcher. Note that this only controls the timezone for the dispatch process, not for the job run itself which will be the local timezone of the worker. See also [Cron and PATH](#cron-and-path).|

### Cron and PATH

Scheduled dispatches are effected by running the Python based `lava-dispatcher`
utility via **cron(8)**. It is **critical** that the `PATH` for **cron** yields
a lava compatible version of Python.

**Cron** typically has a default `PATH` set at a system level that points to
the system default version of Python. This may be an older version that is not
lava compatible. This is the case for the [lava AMI](#the-lava-ec2-ami).


The best way to avoid problems is to explicitly specify the desired `PATH` in
the `env` parameter for the job. e.g.

```json
{
  "parameters": {
    "env": {
      "PATH": "/usr/local/bin:/bin:/usr/bin"
  }
}
```


### Dev Mode Behaviour

The **lavasched** job behaviour is unchanged for dev mode.

### Examples

The following example will cause the crontab to be rebuilt for the `localtime`
dispatcher every hour. It will include jobs that have a `dispatcher` field
of `localtime` - including this **lavasched** job. The dispatch schedule will
operate with respect to the local time set on the worker instance.


```json
{
  "description": "Rebuild the dispatcher crontab",
  "dispatcher": "localtime",
  "enabled": true,
  "job_id": "demo/schedule-01",
  "owner": "demo@somewhere.com",
  "parameters": {
    "dispatcher": "localtime",
    "env": {
      "PATH": "/usr/local/bin:/bin:/usr/bin"
    }
  },
  "payload": "--",
  "schedule": "0 * * * *",
  "type": "lavasched",
  "worker": "default"
}
```

This one does the same but sets the logging level on the `lava-dispatcher`
invocations to `warning`.

```json
{
  "description": "Rebuild the Sydney dispatcher crontab",
  "dispatcher": "Sydney",
  "enabled": true,
  "job_id": "demo/schedule-01",
  "owner": "demo@somewhere.com",
  "parameters": {
    "args": [ "--level", "warning" ],
    "dispatcher": "Sydney",
    "env": {
      "PATH": "/usr/local/bin:/bin:/usr/bin"
    }
  },
  "payload": "--",
  "schedule": "0 * * * *",
  "type": "lavasched",
  "worker": "dispatch_syd"
}
```

This one will cause the dispatcher schedule to operate on Perth time. Note that
the jobs themselves will be dispatched on a Perth schedule but they will run
under whatever timezone setting the worker has.

```json
{
  "description": "Rebuild the Perth dispatcher crontab",
  "dispatcher": "Perth",
  "enabled": true,
  "job_id": "demo/schedule-01",
  "owner": "demo@somewhere.com",
  "parameters": {
    "dispatcher": "Perth",
    "env": {
      "CRON_TZ": "Australia/Perth",
      "PATH": "/usr/local/bin:/bin:/usr/bin"
    }
  },
  "payload": "--",
  "schedule": "0 * * * *",
  "type": "lavasched",
  "worker": "dispatch_perth"
}
```
