

## Handling of Parameters and Globals During Dispatch { data-toc-label="Parameters & Globals During Dispatch" }

In addition to specifying the job to be dispatched, dispatch messages may also
contain job parameter values and named global values. Values specified in the
dispatch message will override any similarly named parameter or global in the
job specification.

This provides a mechanism for job specifications to be more generic, with
specific values being supplied at run-time.

### Job Parameters { data-toc-label="Parameters" }

Job parameters are job type specific and must match the requirements of the job
type. The parameters for a job are determined by the following order of
precedence:

1.  Parameters defined in the dispatch message.

2.  Parameters defined in the job specification.

### Globals

Globals are not job type specific and can be provided to any job type. Moreover,
globals are passed to child jobs by the [chain](#job-type-chain)
[dispatch](#job-type-dispatch) and 
[dag](#job-type-dag) job types. Globals are also
passed to downstream jobs initiated as a result of a
[dispatch](#action-type-dispatch) post-job action.

This then provides a mechanism for a job to receive generic global values when
dispatched (e.g. by an S3 event) which are then made available to
child/downstream jobs, irrespective of job type. Global values are made
available to the Jinja rendering process for any job type that supports this
capability. Refer to individual [job types](#jobs-and-job-types)
for more information.

Global values for a job are determined by the following order of precedence 
(highest to lowest):

1.  Globals in the dispatch message.

2.  Globals in the dispatching job, if any.

3.  Globals in the job specification.

### Globals Owned by Lava

Global names within a job specification may not start with `lava` (case
insensitive). This prefix is reserved for lava's use.

Lava jobs have a concept of *master job* and *parent job*. For a simple,
stand-alone job, the master job, the parent job and the current job are all one
and the same. In a hierarchy of jobs formed when jobs start other jobs via
[chain](#job-type-chain) jobs,
[dispatch](#job-type-dispatch) jobs,
[dag](#job-type-dag) jobs,
or
[dispatch](#action-type-dispatch) post-job actions, the master
job is the initial job at the top of the hierarchy. The parent job is the job
that caused the current job to run.

For a single level hierarchy resulting from a chain job, the master and parent
are the same. In a multi-level hierarchy, they will differ, as shown below.

![][master-parent]

[master-parent]:img/master-parent.png

Lava adds its own globals under `globals.lava` that capture information relating
to the master and parent jobs.

|Name|Type|Description|
|-|-|-------------------------------------------------------------|
|foreach\_index|int|For children of [foreach](#job-type-foreach) jobs, this is the loop iteration counter, starting at zero.|
|iteration|int|The iteration (run attempt) number for the job. See [Job Retries](#job-retries) for more information.|
|master_job_id|str|The `job_id` of the master job.|
|master_start|datetime|The local start time of the master job, including timezone.|
|master_ustart|datetime|The UTC start time of the master job, including timezone.|
|parent_job_id|str|The `job_id` of the parent job.|
|parent_start|datetime|The local start time of the parent job, including timezone.|
|parent_ustart|datetime|The UTC start time of the parent job, including timezone.|

All jobs started from the same master job have access to the `job_id` of the
master job and the local and UTC timestamps for when it started. These can be
useful for constructing Jinja render values that are guaranteed to be
consistent across all jobs started from a common master (e.g. for use in
filenames).

```jinja
{# This might be useful in a filename #}
{{ globals.lava.master_ustart.strftime('%Y-%m-%d') }}
```

### Use with Event Triggered Dispatch

The [s3triggers table](#the-s3triggers-table) permits the
inclusion of globals which will be passed on to any jobs when dispatched.
These will override similarly named globals in the job specification.
