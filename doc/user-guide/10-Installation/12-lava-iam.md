
## Lava IAM Components

The lava [CloudFormation templates](#building-the-cloudformation-templates) will
create a base set of IAM components, both for the lava workers and for users
needing to interact with the lava environment.

These components are described below.

### Lava IAM Roles { data-toc-label="Roles" }

| Role                           | Description                                                  |
| ------------------------------ | - |
| `lava-<REALM>-dispatch-lambda` | Service role for the [dispatch helper](#the-dispatch-helper) Lambda function. |
| `lava-<REALM>-metrics-lambda`  | Service role for the Lambda function that calculates worker backlog metrics used for [lava worker auto scaling](#lava-worker-auto-scaling). |
| `lava-<REALM>-s3trigger`       | Service role for the Lambda function that [dispatches jobs from S3 bucket notification events](#dispatching-jobs-from-s3-events). |
| `lava-<REALM>-stop-lambda`     | Service role for the Lambda function that signals EC2-based lava workers to shutdown as part of an [auto scaler scale-in process](#lava-worker-auto-scaling). |
| `lava-<REALM>-worker-<WORKER>` | IAM role for EC2-based workers. It will have the `lava-<REALM>-worker` policy attached. |

### Lava IAM Policies { data-toc-label="Policies" }

| Policy        | Description |
| ------------- | ----------- |
| `lava-<REALM>-worker` | Base permissions required for a worker node to function within a lava realm. |
| `lava-<REALM>-admin` | Permissions for an administrator for the realm. |
| `lava-<REALM>-reader` | Read-only access to key resources in the realm. |
| `lava-<REALM>-operator` | Additional permissions to that of `lava-<REALM>-reader`.|

### Lava IAM Groups { data-toc-label="Groups" }

IAM groups using the policies described above are also provided:

| Group Name | Policies |
|-|-|
|`lava-<REALM>-admin`|`lava-<REALM>-admin`|
|`lava-<REALM>-reader`|`lava-<REALM>-reader`|
|`lava-<REALM>-operator`|`lava-<REALM>-reader`, `lava-<REALM>-operator`|

The groups have the following permissions, which are restricted to the lava
realm wherever possible:

| Resource                         | Reader | Operator | Admin   |
| -------------------------------- | :----: | :------: | :-----: |
| Lava bucket                      |   R    |    R     |   RW    |
| DynamoDB tables (realm specific) |   R    |    R     |   RW    |
| DynamoDB `realms` table          |   R    |    R     |    R    |
| KMS key `user`                   | Usage  |  Usage   |  Usage  |
| KMS key `sys`                    |        |          |  Usage  |
| Lava distro docker images in ECR |   R    |    R     |    R    |
| Payload docker images in ECR     |   R    |    R     |   RW    |
| EventBridge rules                |   R    |    R     |   RW    |
| Lava worker logs in CloudWatch   |        |    R     |    R    |
| Dispatcher SNS Topic             |        | Publish  | Publish |
| Lava Worker SQS Queues           |        |    R     |   RW    |
| SSM Parameters                   |        |          |   RW    |
| Secrets Manager                  |        |          |   RW    |

!!! note
    The summary above is an approximation. Refer to the actual underlying IAM
    policies for specifics.
