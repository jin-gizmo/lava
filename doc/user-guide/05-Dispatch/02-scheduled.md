
## Scheduled Dispatch

Dispatch events can be scheduled by a *dispatcher*. A dispatcher is just a
worker that runs the [lavasched](#job-type-lavasched) job type.
This job type builds a crontab containing invocations of the `lava-dispatcher`
utility to dispatch jobs in accordance with the schedules specified in the job
specifications.

A realm can have multiple dispatchers. For example, a realm may need to schedule
jobs in multiple timezones (e.g. local and UTC) in which case there would be two
dispatchers, each operating in its respective timezone. However, a given job
must specify a single dispatcher.

The [lavasched](#job-type-lavasched) job must also be dispatched
periodically to create and refresh the crontab. Clearly, there is a chicken and
egg problem here in that an initial dispatch of the
[lavasched](#job-type-lavasched) job is required to create the
first crontab.

There are two ways to achieve this, manually or with a worker jump-start.

### Initialising the Scheduler

The [lavasched](#job-type-lavasched) job can be dispatched
manually whenever required. When dispatching a
[lavasched](#job-type-lavasched) job, the `dispatcher` parameter
must be provided.

```bash
# This command will force the dispatching worker to (re-)build its crontab.
# It will include dispatches for jobs aimed at <DISPATCHER>

lava-dispatcher --realm <REALM> --worker <DISPATCH-WORKER> \
    <LAVASCHED_JOB_ID> --param dispatcher=<DISPATCHER>
```

The problem with this approach is for dispatchers that are started spontaneously
(e.g. by an auto scaler). A manual intervention is then required to dispatch the
first [lavasched](#job-type-lavasched) job or else not much lava
will flow.

### Jump-starting the Scheduler

The lava worker has a `--jump-start` option. When the worker starts, this
option forces it to search the [jobs table](#the-jobs-table)
for any enabled [lavasched](#job-type-lavasched) jobs for which
it is the designated worker and dispatch them immediately.

This option is safe to use on any worker but does require a full scan of the
[jobs table](#the-jobs-table).

### Scheduling the Scheduler

Of course, the [lavasched](#job-type-lavasched) jobs should
also have their own schedule specified to refresh the crontab as changes are
made in the [jobs table](#the-jobs-table). It is recommended to
schedule the [lavasched](#job-type-lavasched) jobs to run every
10 or 15 minutes. The job makes a reasonable effort to avoid updating the
crontab when nothing has changed. It is also careful to avoid disturbing
entries in the crontab that don't belong to lava.

### Matching Jobs to Dispatchers

This is a typical job specification for a
[lavasched](#job-type-lavasched) job. Note the two different
`dispatcher` items that serve related but separate purposes.

```json
{
  "description": "Rebuild the crontab for the dispatcher",
  "dispatcher": "Sydney",
  "enabled": true,
  "job_id": "...",
  "owner": "...",
  "parameters": {
    "dispatcher": "Sydney",
    "env": {
      "CRON_TZ": "Australia/Sydney",
      "PATH": "/usr/local/bin:/bin:/usr/bin"
    }
  },
  "payload": "--",
  "schedule": "0-59/15 * * * *",
  "type": "lavasched",
  "worker": "core"
}
```

!!! info
    This PATH specification in the environment clause above is **critical** when
    using the [lava AMI](#the-lava-ec2-ami). If not specified, **cron** will use
    the default system version of Python rather than the preferred version
    installed in `/usr/local/bin` and the dispatcher may fail. Silently.

Each [lavasched](#job-type-lavasched) job specification must
contain both

1.  A `dispatcher` field in the job specification.

    This indicates which dispatcher will dispatch the
    [lavasched](#job-type-lavasched) job itself.

2.  A `dispatcher` parameter in the job specifications `parameter` object.

    This indicates which jobs will be included in the crontab built by the job.
    It is matched against the `dispatcher` field for all jobs in the table.

### Suspending the Scheduler

If there is a need to temporarily disable scheduled job dispatch from a given
dispatcher, change **both** of the `dispatcher` values in the
[lavasched](#job-type-lavasched) job specification to a value
that will not match any other job. Once the crontab updates, no jobs other than
the [lavasched](#job-type-lavasched) job will be run. This is
much simpler than changing all of the other jobs and still allows the scheduled
dispatch process to be re-enabled when required.

For example:

```json
{
  "description": "Rebuild the crontab for the dispatcher",
  "dispatcher": "**Disabled** Sydney",
  "enabled": true,
  "job_id": "...",
  "owner": "...",
  "parameters": {
    "dispatcher": "**Disabled** Sydney",
    "env": {
      "CRON_TZ": "Australia/Sydney",
      "PATH": "/usr/local/bin:/bin:/usr/bin",
    }
  },
  "payload": "--",
  "schedule": "0-59/15 * * * *",
  "type": "lavasched",
  "worker": "core"
}
```

### Schedule Specifications

Each job that is to be dispatched on a schedule must have a `schedule` field in
the job specification that is used to derive the time component of the
dispatcher crontab entries.

The value of this field is either:

*   A string containing a conventional crontab timing specification.

*   A [lava scheduling object](#lava-scheduling-objects) as
    described below.

*   A list of an arbitrary mixture of the above.

This means that one job can have multiple crontab entries to allow more complex
scheduling permutations without the need to duplicate the entire job
specification.

!!! info
    The syntax of crontab strings must be compatible with the dispatch worker's
    cron implementation. It is strongly recommended to avoid the non-standard
    extensions to cron found on some systems. [Crontab Guru](https://crontab.guru)
    is a useful syntax helper / checker. Having said that, some of the `@`
    forms can be useful shortcuts. The `@reboot` form is a bit special in that it
    will be dispatched only when the dispatcher node reboots.

#### Lava Scheduling Objects

A *lava scheduling object* is a map with the following fields:

|Field|Type|Required|Description|
|-|-|-|-------------------------------------------------------------|
|crontab|String|Yes|A conventional crontab timing specification.|
|from|String|No|An ISO 8601 datetime string specifying when the schedule object becomes active. Default is midnight, 01/01/0001|
|to|String|No|An ISO 8601 datetime string specifying when the schedule object ceases to active. Default is midnight, 31/12/9999|

The `from` and `to` fields allow specific schedules to be active only within
defined time periods. If `from` is less than `to`, the schedule is active only
between those two times. If `from` is greater than `to`, the schedule is active
only outside those two times.

![][from-to]

[from-to]:img/schedule-from-to.png

The `from` and `to` fields are each timezone aware. If no timezone is specified, the
local timezone of the worker running the
[lavasched](#job-type-lavasched) job is assumed.

#### Examples

The simplest form of schedule is a simple crontab string:

```json
{
  ...
  "schedule": "0 12 * * Mon",
  ...
}
```

This one will run the job at midday on weekdays and 2pm on weekends.

```json
{
  ...
  "schedule": [
    "0 12 * * 1-5",
    "0 14 * * 0,6"
  ],
  ...
}
```

This one will run the job daily at midday before 30 June 2019 and daily at 2pm
after that. Note that in this example, UTC is specified in the date entries.

```json
{
  ...
  "schedule": [
    {
      "crontab": "0 12 * * *",
      "to": "2019-06-30T00:00:00Z"
    },
    {
      "crontab": "0 14 * * *",
      "from": "2019-06-30T00:00:00Z"
    }
  ],
  ...
}
```

This one will run the job daily at midday, except during February 2019 when it
is not active. Note that `from` is greater than `to` in this case and the lack
of timezone means the local timezone of the worker running the
[lavasched](#job-type-lavasched) job will be used.

```json
{
  ...
  "schedule": {
    "crontab": "0 12 * * *",
    "from": "2019-03-01T00:00:00",
    "to:": "2019-02-01T00:00:00"
  },
  ...
}
```
