
# Lava Architecture { x-nav="Architecture" }

Each lava realm has the following components:

*   A few [DynamoDB tables](#dynamodb-tables).

*   [S3 locations](#lava-s3-locations) for payloads
    and job outputs.

*   One or more [SQS queues](#sqs-queues) to feed jobs to
    workers.

*   One or more [workers](#lava-workers).

*   Zero or more [dispatchers](#lava-dispatchers).

*   [Auxiliary components](#auxiliary-components), such as IAM
    roles, SNS topics for notices etc.

*   Optional [Lambda functions](#dispatching-jobs-from-s3-events)
    for triggering jobs from S3 events and assisting external programs to
    request job dispatches.

*   A few other AWS bits and pieces.

Most of these components are created by the CloudFormation templates provided
with lava. See [Installation](#lava-installation-and-operation)
for more information.

A typical realm configuration is shown below.

![Lava Architecture][arch]

[arch]:img/lava-architecture.png
