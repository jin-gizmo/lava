
# Concepts

Lava is based on the following concepts.

## Realms

A lava realm is a completely self-contained lava deployment. A realm has its own
dedicated [configuration tables](#dynamodb-tables),
[jobs](#jobs), [dispatchers](#dispatchers),
[workers](#workers),
[S3 payload storage](#payloads) and security controls.

## Jobs

A job is a lava unit of work. Jobs are sent by a *dispatcher* to *workers*,
either on demand, based on a cron style schedule, in response to an S3 bucket
notification event, or in response to an Amazon EventBridge event. Each
invocation of a job is a *job run* and is assigned a UUID. This UUID is used in
the naming of job outputs in S3 and in event logging.  Various job types are
supported, depending on the kind of processing required.

In most cases, a job will run within seconds of being dispatched. When a job is
run, it inherits the local timezone of the worker. For those job types that
support environment variable parameters (e.g. the
[exe job type](#job-type-exe) and
[pkg job type](#job-type-pkg), this can be modified by setting
the `TZ` environment variable. It is important to understand that the dispatcher
and the worker may operate in different timezones. The dispatcher timezone
controls *when* the job runs. The worker timezone controls the timezone in which
the job runs.

## Workers

Workers are Linux based nodes that receive *jobs* from *dispatchers* via AWS SQS.

A *realm* can have one or more worker fleets with each fleet having one or more
worker nodes. All workers in a fleet must have the same capabilities but
different fleets can have different capabilities.

For example, it's possible to have one fleet of workers dedicated to short jobs
that require minimal computational power and a second fleet dedicated to jobs
requiring significant computation. Jobs are dispatched to whichever fleet is
specified in the job configuration.

Workers can be AWS EC2 nodes but do not have to be. Any Linux node with Python
3.9+ installed can be a worker.

EC2 based worker fleets can be set to auto scale if required.

## Handlers

The *worker* uses a simple plugin mechanism to handle *jobs* of different types.
Each such plugin handles a given *job* type.

Current handlers support actions such as running SQL, running executables and
building the lava crontab on a *dispatcher*. It is relatively straightforward
to add new handlers.

## Dispatchers

Dispatchers send job run instructions to *workers* via AWS SQS. If a *realm*
is to have scheduled jobs, then it must have at least one dispatcher.

A *realm* can have multiple dispatchers. For example, a realm may need to
schedule jobs in two different timezones (e.g. local and UTC) in which case
there would be two dispatchers, each operating in its respective timezone.
However, a given job must specify a single dispatcher.

A dispatcher is just a special kind of worker that uses the onboard *cron*
daemon to send dispatch messages. Like all workers, it is stateless and the
crontab is built behind the scenes automatically by a special job type.

Refer to [The Lava Dispatch Process](#the-lava-dispatch-process)
for more information.

## Payloads

Each *job* has an associated payload. This is typically the code bundle that is
to be executed for the *job*. Payloads are stored in an area of S3 dedicated to
the *realm*.

## Actions

For each *job*, it is possible to specify actions that are to be performed when
the *job* completes, fails or retries. Actions include things such as
dispatching other jobs or sending messages via SQS, SNS, email etc.
