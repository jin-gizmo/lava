
## Job type: dag

The **dag** (**D**irected **A**cyclic **G**raph) job type runs a set of child
jobs in the order defined by a dependency matrix.

Ordering controlled by explicit dependencies will be honoured in that a child
job which is a predecessor of another child job will always run to completion
before the successor job starts.  Except for this, there is no guaranteed run
order for the child jobs. Jobs that are not dependent on one another may run in
any order, or in parallel.

All of the jobs in the DAG must be set to run on the same worker and will all
run under the `run_id` of the parent job. The jobs will be run in a dedicated
transient thread pool that is separate from the main lava worker threads.

Any globals available in the **dag** job will also be passed to the child jobs.

### Payload

The `payload` is a map containing elements in the form:

```json
{
  "payload": {
    "child_job_id_1": "predecessor_job_id",
    "child_job_id_2": [ List of predecessor job IDs ],
    "child_job_id_3": null,
    "child_job_id_4": []
  }
}
```

The keys are job IDs and values must be one of the following:

1.  The ID of a predecessor job as a string.

2.  A list of predecessor job IDs.

3.  A `null` indicating the job must be run but has no predecessor requirements.

4.  An empty list, which also indicates the job must be run but has no
    predecessor requirements.
    
!!! info
    *Every* job listed in the payload map, in either a key, or as an element in
    a predecessor list, will be run exactly once by the **dag** job.

It is not necessary to include a separate key for a job if it is also present in
a predecessor list and has no predecessors of its own, but it's harmless to do
so.

!!! note
    The [lava-dag-gen](#lava-dag-generator) utility generates a **dag** job
    payload from a dependency matrix. It can be used standalone or with the
    [lava job framework](#the-lava-job-framework).

### Parameters

|Parameter|Type|Required|Description|
|-|-|-|-------------------------------------------------------------|
|can\_fail|String *or* List[String]|No|A glob style pattern, or list of patterns specifying child jobs that are allowed to fail. See [Allowing Child Jobs to Fail](#allowing-child-jobs-to-fail).|
|job\_prefix|String|No|Prepend the specified value to each job ID in the payload.|
|workers|Integer|No|The number of worker threads to use for running child jobs. The default is specified by the [DAG_WORKERS](#configuration-for-dag-jobs) worker configuration parameter and the maximum allowed value is specified by the [DAG_MAX_WORKERS](#configuration-for-dag-jobs) configuration parameter.|

!!! tip
    Don't get carried away setting the `workers` parameter too high. It will
    impact memory consumption.


### Allowing Child Jobs to Fail
By default, the **dag** job is aborted when any child fails, however child jobs
running in parallel with the failed job will generally run to completion.

The `can_fail` parameter can be set to a glob style pattern, or list of
patterns.  A failed child job with a `job_id` that matches any of the patterns
will not cause the parent **dag** job, or dependent jobs, to fail. In this
situation, it is important that the child job handles its own
[on\_fail](#job-actions) actions, as the parent will not. Tough love.

This tolerance of failure does not include configuration errors on child jobs,
such as malformed job specifications, jobs sent to the wrong worker etc. These
will still cause the entire **dag** job to fail.

### Handling of Globals

The **dag** job type merges its globals into those of the child jobs.  A value
specified in the parent **dag** job will override a similarly named value in the
child.

The **dag** job will also add
[lava specific globals](#globals-owned-by-lava) under
`globals.lava`. These lava owned globals allow all child jobs in the dag to
access some common global values.

### Dev Mode Behaviour

The **dag** job behaviour is unchanged for dev mode. However, dev mode is
propagated to child jobs.

### Examples

```json
{
  "description": "Daggy job",
  "dispatcher": "Sydney",
  "enabled": true,
  "job_id": "demo/dag-01",
  "owner": "demo@somewhere.com",
  "parameters": {
    "workers": 2
  },
  "payload": {
    "demo/job_01": "demo/job_02",
    "demo/job_02": [ "demo/job_03", "demo/job_04" ],
    "demo/job_05": null
  },
  "schedule": "0 0 * * *",
  "type": "dag",
  "worker": "default"
}
```

This version uses `job_prefix` and is functionally identical to the one above:

```json
{
  "description": "Daggy job",
  "dispatcher": "Sydney",
  "enabled": true,
  "job_id": "demo/dag-01",
  "owner": "demo@somewhere.com",
  "parameters": {
    "job_prefix": "demo/",
    "workers": 2
  },
  "payload": {
    "job_01": "job_02",
    "job_02": [ "job_03", "job_04" ],
    "job_05": null
  },
  "schedule": "0 0 * * *",
  "type": "dag",
  "worker": "default"
}
```

An uncaring parent **dag** job that doesn't care if any of its children fail:

```json
{
  "description": "Daggy job",
  "dispatcher": "Sydney",
  "enabled": true,
  "job_id": "demo/dag-01",
  "owner": "demo@somewhere.com",
  "parameters": {
    "can_fail": "*",
    "workers": 2
  },
  "payload": {
    "demo/job_01": "demo/job_02",
    "demo/job_02": [ "demo/job_03", "demo/job_04" ],
    "demo/job_05": null
  },
  "schedule": "0 0 * * *",
  "type": "dag",
  "worker": "default"
}
```

A parent **dag** job that plays favourites:


```json
{
  "description": "Daggy job",
  "dispatcher": "Sydney",
  "enabled": true,
  "job_id": "demo/dag-01",
  "owner": "demo@somewhere.com",
  "parameters": {
    "can_fail": [
      "*/job_[24]"
    ],
    "workers": 2
  },
  "payload": {
    "demo/job_01": "demo/job_02",
    "demo/job_02": [ "demo/job_03", "demo/job_04" ],
    "demo/job_05": null
  },
  "schedule": "0 0 * * *",
  "type": "dag",
  "worker": "default"
}
```
