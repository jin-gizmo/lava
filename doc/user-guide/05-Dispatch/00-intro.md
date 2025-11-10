
# The Lava Dispatch Process { x-nav="Job Dispatch" }

The underlying mechanism for the lava job dispatch process is very simple. A
JSON formatted message containing a job ID is sent via AWS SQS to a worker. The
SQS queue for any worker is named `lava-<REALM>-<WORKER>`.

The worker retrieves the message, extracts the job details from the [jobs
table](#the-jobs-table) and then runs the job if it is enabled
and the worker is the one named in the job specification.

There are several mechanisms that can initiate the sending of the SQS dispatch
message:

*   [Scheduled dispatch](#scheduled-dispatch)

*   [Job initiated dispatch](#job-initiated-dispatch)

*   [AWS S3 event triggered dispatch](#dispatching-jobs-from-s3-events)

*   [Amazon EventBridge triggered dispatch](#dispatching-jobs-from-amazon-eventbridge)

*   [The Dispatch Helper](#the-dispatch-helper)

*   [Direct dispatch](#direct-dispatch).
