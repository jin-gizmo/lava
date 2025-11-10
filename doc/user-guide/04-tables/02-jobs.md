
## The Jobs Table { data-toc-label="Jobs" }

The jobs table for a given `<REALM>` is named `lava.<REALM>.jobs`. It contains
information about jobs and their associated run information.

|Field|Type|Required|Description|
|-|-|-|-------------------------------------------------------------|
|cw\_metrics|Boolean|No|If specified, enable/disable generation of [CloudWatch custom metrics](#cloudwatch-metrics) for this job. If present, overrides any value set at the worker/realm level.|
|description|String|Not yet|A short description of the job. **This field will be mandatory in a future release.**|
|dispatcher|String|No|An identifier specifying the [dispatcher](#lava-dispatchers) for the job.|
|enabled|Boolean\|String|No|Whether or not the job is enabled. Defaults to `false`. String values are Jinja rendered, providing a means to dynamically enable / disable jobs at run-time. [More information](#the-enabled-field).|
|event\_log|\*|No|The specified value is Jinja rendered and recorded as part of the job run event information in the [events table](#the-events-table). [More information](#the-event_log-field).
|globals|Map[String,\*]|No|A map of named values that are made available for Jinja rendering of [job actions](#job-actions) and job parameters for those job types that use Jinja parameter rendering. Names beginning with `lava` (case insensitive) are reserved for lava's use. [More information on parameters and globals](#handling-of-parameters-and-globals-during-dispatch).|
|iteration_delay|String|No|The delay between attempts to run the job in the form nnX where nn is a number and X is s (seconds) or m (minutes). Default is `0s`. The maximum allowed value is specified by the [ITERATION_MAX_DELAY](#general-configuration-parameters) configuration parameter. See [Job Retries](#job-retries) for more information.|
|iteration_limit|Integer|No|The number of attempts that will be made to run the job. Default is 1. The maximum allowed value is specified by the [ITERATION_MAX_LIMIT](#general-configuration-parameters) configuration parameter. This is unrelated to the SQS related `max_tries` parameter. See [Job Retries](#job-retries) for more information.|
|job\_id|String|Yes|The unique job identifier for the realm. It is possible to have some grouping of jobs using a path like structure. e.g. `job_group/myjob_01`.|
|max\_run\_delay|String|No|The maximum allowed delay between when a job is dispatched and when it is run in the form `nnX` where `nn` is a number and `X` is `s` (seconds), `m` (minutes), `h` (hours) or `d` (days). If this limit is exceeded, the job run is discarded with an error. If not specified, no limit is imposed other than the message retention period of the worker SQS job queue.|
|max\_tries|Number|No|By default, if a lava worker fails mid-job, SQS will resubmit the dispatch request at the end of the visibility timeout. If `max_tries` is set to a positive integer value, then the dispatch message will be discarded when the SQS message `ApproximateReceiveCount` exceeds the specified value. Note that the minimum of the value of the `Maximum Receives` value for the worker SQS queue (if set) and any limit specified by the `--retries` worker option is still the upper limit.|
|on\_fail|List[Map]|No|Job specific [on_fail actions](#job-actions) for the job. Overrides any realm level setting.|
|on\_retry|List[Map]|No|Job specific [on_retry actions](#job-actions) for the job. Overrides any realm level setting.|
|on\_success|List[Map]|No|Job specific [on_success actions](#job-actions) for the job. Overrides any realm level setting.|
|owner|String|Not yet|Name or email address of the job owner. **This field will be mandatory in a future release.**|
|parameters|Map[String,\*]|No|A map of parameters that will be passed to the job. The parameter structure is dependent on the [job type](#jobs-and-job-types).|
|payload|*|Yes|The job payload. The type and format is job type dependent. Currently, a value is required even for job types that do not need it. In this case set the value to `null`.|
|schedule|String|No|A [cron](https://crontab.guru) schedule that specifies when the job will run. Refer to the section [Schedule Specifications](#schedule-specifications) for more information. If not specified, the job can be dispatched on demand but will not be scheduled.|
|state|Map[String,\*]|No|A map of [state items](#the-lava-state-manager). For each item, the key is the `state_id` and the value is a default value. The default values are replaced at run-time by the current value of the specified state item in the [state](#the-state-table) table, if it exists.|
|type|String|Yes|The name of the [job handler](#jobs-and-job-types) to run.|
|worker|String|Yes|The name of a worker that can run the job.|
|X-\*|String|No|Any fields beginning with `x-` or `X-` are ignored by lava. These can be used as required for other purposes (e.g. CI/CD, versioning or other related purposes). The [lava job framework](#the-lava-job-framework) uses a number of these fields for various purposes.|

!!! warning
    Currently, unknown fields in the job specification will result in a
    deprecation warning being written to the worker's log but the job is permitted
    to run. A future release will reject jobs that have unknown fields.

### The enabled Field

Prior to v8.0 (Incahuasi), the `enabled` field was a simple, static boolean
value. If `false`, the job would be skipped. This behaviour is unchanged in
v8+ if the value is boolean.

If the value is a string, it is Jinja rendered. If the resulting value is the
string `true` (case and surrounding whitespace are ignored), the job is enabled
to run. Any other value will result in the job being skipped. This allows job
execution to be conditional on run-time values. 

The following variables are made available to the Jinja renderer.

|Name|Type|Description|
|-|-|-------------------------------------------------------------|
|globals|dict[str,\*]|The `globals` from the job specification updated with any globals received in the job dispatch.|
|job|dict[str,\*]|The [augmented job specification](#the-augmented-job-specification).|
|realm|dict[str,\*]|The realm specification.|
|start|datetime|The local time when the job run started.|
|state|dict[str,\*]|A dictionary of the state items imported into the job, keyed on state_id. The default values are updated at run-time with any current values obtainable from the [state](#the-state-table) table.|
|ustart|datetime|The UTC time when the job run started.|
|utils|dict[str,runnable]|A dictionary of [utility functions](#jinja-utility-functions) that can be used in the Jinja markup.|

As an example, the following job specification fragment will only enable the
job if the value of the global `a` is palindromic (which it is, in the example):

```json
{
  "enabled": "{% set word = globals.a | lower %}{{ word == word | reverse }}",
  "globals": {
    "#": "Global a is a palindrome.",
    "a": "Tattarrattat"
  }
}
```

In this example, the job is only enabled if the value of the `x` field in
[state](#the-state-table) item `sid` is odd:

```json
{
  "enabled": "{% set val = state['sid'].x | int %}{{ val % 2 == 1 }}",
  "state": {
    "sid": "-- set at run-time --"
  }
}
```

As a more complex example, this job specification fragment only enables a
job if it has not run successfully in the last 4 hours:

```json
{
  "schedule": "30 * * * *",
  "enabled": "{% set ts=utils.parsedate.parse(state['sid']) %}{{ ustart-ts > utils.timedelta(hours=4) }}",
  "on_success": [
    {
      "action": "state",
      "state_id": "sid",
      "value": "{{ ustart.isoformat() }}"
    }
  ],
  "state": {
    "sid": "2000-01-01T00:00:00Z"
  },
  "event_log": "Time since last run: {% set ts=utils.parsedate.parse(state['sid']) %}{{ ustart-ts }}"

}
```

Some points to note:

*   A state variable is declared to hold an ISO 8601 datetime containing the
    last successful run-time for the job. This has an initial value defined in
    the job specification.

*   The `enabled` field checks the start time of the current run against the
    previous run start time, to ensure the required period of time has passed
    (4 hours in the example).

*   Once the job runs, an `on_success` action creates a state item that records
    the start time of the successful run.

*   An `event_log` field records for posterity the time since the previous run.

### The event\_log Field

Jobs may receive critical configuration as part of the dispatch process
via parameters, globals, and state items. It can be tricky to determine from the
[events table](#the-events-table) exactly what a job run was doing, particularly
in the event that a job run fails.

While it would be possible to record the entire
[augmented job specification](#the-augmented-job-specification), this is not
safe in all cases as sensitive values may be exposed in the
[events table](#the-events-table).

The `event_log` field allows the job specification to specify that certain
information should be recorded in the job run record in the
[events table](#the-events-table). The value of the field is an arbitrary
object that will be Jinja rendered and added to the
[events table](#the-events-table) before the first iteration of the job begins.
this information is added in a new entry with a `logging` status in the `log`
field of the event record.

The following variables are made available to the Jinja renderer.


|Name|Type|Description|
|-|-|-------------------------------------------------------------|
|globals|dict[str,\*]|The `globals` from the job specification updated with any globals received in the job dispatch.|
|job|dict[str,\*]|The [augmented job specification](#the-augmented-job-specification).|
|realm|dict[str,\*]|The realm specification.|
|start|datetime|The local time when the job run started.|
|state|dict[str,\*]|A dictionary of the state items imported into the job, keyed on state_id. The default values are updated at run-time with any current values obtainable from the [state](#the-state-table) table.|
|ustart|datetime|The UTC time when the job run started.|
|utils|dict[str,runnable]|A dictionary of [utility functions](#jinja-utility-functions) that can be used in the Jinja markup.|

As an example, the following job specification fragment would record the value
of a specific global.

```json
{
  "event_log": "The value of global g1 is '{{ globals.g1 }}'"
}
```

This fragment would record two globals in a map format:

```json
{
  "event_log": {
    "g1": "{{ globals.g1 }}",
    "g2": "{{ globals.g2 }}"
  }
}
```

This fragment would record all of the globals (as a Python object converted to
a string):

```json
{
  "event_log": "{{ globals }}'"
}
```

!!! warning
    **DO NOT** be cavalier with this. Take care to avoid logging sensitive
    information.
