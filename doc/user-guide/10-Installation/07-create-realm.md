## Creating a Lava Realm

A lava realm is created using the following process:

1.  [Create the realms table](#creating-the-realms-table), if it doesn't already
    exist.
2.  [Add an entry in the realms table](#adding-a-new-entry-to-the-realms-table)
    for the new realm.
3.  [Use the realm CloudFormation template](#the-lava-realm-cloudformation-template)
    to create the AWS resources for the realm.

Once the realm is configured, there may be a few final items to perform, such as

*   Add a resource policy to the lava realm S3 bucket, if required.

*   Add subscriptions to the realm SNS topic for event notifications.

*   Configure connections and jobs for the realm.

### Creating the Realms Table

There is a single [realms table](#the-realms-table) per AWS account. While it
*can* be created by the CloudFormation template that creates an individual
realm, this is not recommended as it means the resulting stack cannot be deleted
without impacting other lava realms.

The recommended way to create the realms table is using the following command:

```bash
# Create the realms table. ReadCapacityUnits can be adjusted now or once the
# table is created. WriteCapacityUnits does not need to be changed.

aws dynamodb create-table --table-name lava.realms \
    --key-schema AttributeName=realm,KeyType=HASH \
    --attribute-definitions AttributeName=realm,AttributeType=S \
    --provisioned-throughput ReadCapacityUnits=3,WriteCapacityUnits=1
```

### Adding a New Entry to the Realms Table { data-toc-label="Adding a Realms Table Entry" }

Each realm requires an entry in the [realms table](#the-realms-table). This will
look something like the following: (replace `<..>` with the appropriate value).

```json
{
  "on_fail": [
    {
      "action": "sns",
      "message": "Job {{job.job_id}}@{{realm.realm}} ({{job.run_id}}) failed: {{result.error}}",
      "topic": "arn:aws:sns:<REGION>:<ACCOUNT_ID>:lava-<REALM>-notices"
    }
  ],
  "realm": "<REALM>",
  "s3_key": "alias/lava-<REALM>-user",
  "s3_payloads": "s3://<lavaBucketName>/payloads",
  "s3_temp": "s3://<lavaBucketName>/tmp"
}
```

### The Lava Realm CloudFormation Template { data-toc-label="Realm CFN Template" }

!!! note
    Pre-built versions of the CloudFormation templates are provided as part of
    a [release on GitHub](https://github.com/jin-gizmo/lava/releases).

The [realm CloudFormation template](#lava-realmcfnjson) is located in the
[lava repo](#the-lava-repo).
See [Building the CloudFormation Templates](#building-the-cloudformation-templates).

If the realm is going to host any workers, the 
[lava lambda function code bundles](#building-the-lava-lambda-function-code-bundles)
must also have been built and [deployed to S3](#deploying-lava-components).

!!! note
    It is possible, and sometimes useful, to create a *bare realm* that will not
    contain any workers. In this situation, the realm consists only of the
    DynamoDB tables and a few other static components. A bare realm is useful
    where an external application needs to use the lava connector subsystem via
    the [jinlava API][lava.connection] but is not necessarily being orchestrated
    to run on a lava worker.

The template incorporates the following resources:

*   The realm specific [DynamoDB tables](#dynamodb-tables).
*   The S3 bucket for the realm that will contain job payloads and outputs.
*   Some KMS keys for the realm.
*   An SNS topic for notifications relating to the realm.
*   Lambda functions for the S3 job trigger and dispatch helper and associated
    IAM roles.
*   Realm specific [IAM components](#lava-iam-components).

Template parameters are described below.

| Parameter                   | Required | Description                                                  |
| --------------------------- | -------- | ------------------------------------------------------------ |
| Version                     | Yes      | This is a **read-only** informational parameter that indicates the lava version associated with the template. |
| autoscalingHeartbeatMinutes | Yes      | Send auto scaling heartbeats at this frequency when workers are terminating. This tells the auto scaler that the worker is still busy finishing in-flight jobs and to give it more time before forced termination. The upper limit on the auto scaler's patience is set by the `workerStopMinutes` parameter. |
| createRealmsTable           | Yes      | If `yes`, the [realms](#the-realms-table) table will be created. It's much safer to leave this set to `no` and [create the realms table](#creating-the-realms-table) separately. |
| kmsKeyAdmin                 | Yes      | The IAM user name of KMS key administrator. This gets added into the resource policy of the realm's KMS keys. |
| lambdaMetricsSchedule       | Yes      | If set to `ENABLED`, an AWS EventBridge rule fires the `lava-<REALM>-metrics` lambda once a minute. This lambda calculates the worker backlog metric used to manage [lava worker auto scaling](#lava-worker-auto-scaling). |
| lambdaTimeout               | Yes      | Timeout for the lambdas (seconds). Ignored if the lambdas are not deployed. |
| lambdaVersion               | No       | This parameter selects which code version is deployed for the Lambda functions. If left empty, the Lambda functions are not deployed. |
| lavaBucketName              | Yes      | The name of the bucket where the new realm will store job payloads and outputs. The template will create this bucket. |
| logBucketName               | Yes      | Name of S3 bucket for S3 logs.                               |
| readCapacityDataTables      | Yes      | Read capacity for the [Dynamo DB data tables](#dynamodb-tables). This excludes the [events](#the-events-table) table and the [state](#the-state-table) table. |
| readCapacityEventTable      | Yes      | Read capacity for the [events](#the-events-table) table.     |
| readCapacityStateTable      | Yes      | Read capacity for the [state](#the-state-table) table.       |
| realm                       | Yes      | Realm name.                                                  |
| s3CodeBucket                | Yes      | The name of the bucket containing the lava code bundles.     |
| s3CodePrefix                | Yes      | The prefix in the code bucket containing the lava code bundles. |
| tmpExpiryDays               | Yes      | Expire files in the temp area of the lava bucket after this many days. |
| workerStopMinutes           | Yes      | Allow workers this many minutes to stop gracefully. When a worker is instructed to shut down by its owning auto scaling group, it is given the specified amount of time to finish any in-flight jobs before the auto scaler forcibly terminates it. This value can be as high as 720 minutes (12 hours). The value should be selected in conjunction with the worker SQS queue visibility timeout. |
| writeCapacityDataTables     | Yes      | Write capacity for the [Dynamo DB data tables](#dynamodb-tables). This excludes the [events](#the-events-table) table and the [state](#the-state-table) table. |
| writeCapacityEventTable     | Yes      | Write capacity for the [events](#the-events-table) table.    |
| writeCapacityStateTable     | Yes      | Write capacity for the [state](#the-state-table) table.      |

