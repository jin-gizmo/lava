
## SQS Queues

Dispatchers place messages for each job run on an SQS queue where it is picked
up by a worker and executed.

For a given `<REALM>` and `<WORKER>`, the SQS queue name must be
`lava-<REALM>-<WORKER>`.

When setting up the queue, it's important to give proper consideration to the
visibility timeout and message retention period properties. The visibility 
timeout must be long enough for workers to process jobs otherwise SQS will
resubmit the message for another run before the run is finished.

An SQS queue for each worker is created by the [CloudFormation
templates](#lava-installation-and-operation).
