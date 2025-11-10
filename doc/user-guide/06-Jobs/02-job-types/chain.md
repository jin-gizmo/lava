
## Job type: chain

The **chain** job type runs a list of other jobs sequentially. Unlike the
[dispatch](#job-type-dispatch) job type, this is a synchronous
operation. All of the jobs in the chain must be set to run on the same worker
and will all run under the `run_id` of the parent job.

It is possible to commence processing of a chain at an arbitrary point in the
list. This is useful when it's necessary to resume a failed chain at a mid-point.

Any globals available in the **chain** job will also be passed in the dispatch
requests to the jobs in the chain.

### Payload

The `payload` is either a comma separated list of `job_id`s or an actual list of
`job_id`s.

### Parameters

|Parameter|Type|Required|Description|
|-|-|-|-------------------------------------------------------------|
|can\_fail|String *or* List[String]|No|A glob style pattern, or list of patterns specifying child jobs that are allowed to fail. See [Allowing Child Jobs to Fail](#allowing-child-jobs-to-fail).|
|job\_prefix|String|No|Prepend the specified value to each job ID in the payload, including any job specified by the `start` parameter.|
|start|String|No|The `job_id` of the starting point in the chain. The chain will commence with the first job with the given ID.|

### Allowing Child Jobs to Fail

By default, the chain is aborted when any job in the list fails unless the
`can_fail` parameter is specified, however jobs that are not enabled will be
skipped and the chain will continue.

The `can_fail` parameter can be set to a glob style pattern, or list of
patterns.  A failed child job with a `job_id` that matches any of the patterns
will not cause the parent chain to fail. In this situation, it is important that
the child job handles its own [on\_fail](#job-actions) actions, as the parent
will not. Tough love.

This tolerance of failure does not include configuration errors on child jobs,
such as malformed job specifications, jobs sent to the wrong worker etc. These
will still cause the entire chain to fail.

!!! note "Keep calm"
    Before anyone gets all bitter and twisted about *can* vs *may* in
    `can_fail`...  both are essentially equivalent in this crazy, modern world.
    Look it up.

### Handling of Globals

The **chain** job type merges its globals into those of the child jobs in the
chain. A value specified in the parent **chain** job will override a similarly
named value in the child.


The **chain** job will also add
[lava specific globals](#globals-owned-by-lava) under
`globals.lava`. These lava owned globals allow all jobs in a chain, even a 
multi-level chain, to access some common global values.

### Dev Mode Behaviour

The **chain** job behaviour is unchanged for dev mode. However, dev mode is
propagated to jobs in the chain.

### Examples

A basic chain:

```json
{
  "description": "Chain, chain, chain ... Chain of tools",
  "dispatcher": "Sydney",
  "enabled": true,
  "job_id": "demo/chain-01",
  "owner": "demo@somewhere.com",
  "parameters": {},
  "payload": [
    "demo/job_01",
    "demo/job_02"
  ],
  "schedule": "0 0 * * *",
  "type": "chain",
  "worker": "default"
}
```

The chain with a different starting point:

```json
{
  "description": "Chain, chain, chain ... Chain of tools",
  "dispatcher": "Sydney",
  "enabled": true,
  "job_id": "demo/chain-01",
  "owner": "demo@somewhere.com",
  "parameters": {
    "start": "demo/job_02"
  },
  "payload": [
    "demo/job_01",
    "demo/job_02"
  ],
  "schedule": "0 0 * * *",
  "type": "chain",
  "worker": "default"
}
```

With a common job prefix:

```json
{
  "description": "Chain, chain, chain ... Chain of tools",
  "dispatcher": "Sydney",
  "enabled": true,
  "job_id": "demo/chain-01",
  "job_prefix": "demo/",
  "owner": "demo@somewhere.com",
  "parameters": {
    "start": "job_02"
  },
  "payload": [
    "job_01",
    "job_02"
  ],
  "schedule": "0 0 * * *",
  "type": "chain",
  "worker": "default"
}
```

An uncaring parent chain job that doesn't care if any of its children fail:


```json
{
  "description": "Chain, chain, chain ... Chain of tools",
  "dispatcher": "Sydney",
  "enabled": true,
  "job_id": "demo/chain-01",
  "owner": "demo@somewhere.com",
  "parameters": {
    "can_fail": "*"
  },
  "payload": [
    "demo/job_01",
    "demo/job_02"
  ],
  "schedule": "0 0 * * *",
  "type": "chain",
  "worker": "default"
}
```

A parent chain job that plays favourites:


```json
{
  "description": "Chain, chain, chain ... Chain of tools",
  "dispatcher": "Sydney",
  "enabled": true,
  "job_id": "demo/chain-01",
  "owner": "demo@somewhere.com",
  "parameters": {
    "can_fail": [
      "*/job_[0-9][0-9]"
    ]
  },
  "payload": [
    "demo/job_01",
    "demo/job_02",
    "demo/black_sheep"
  ],
  "schedule": "0 0 * * *",
  "type": "chain",
  "worker": "default"
}
```
