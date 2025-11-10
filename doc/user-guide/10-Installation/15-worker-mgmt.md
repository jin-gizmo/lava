
## Lava Worker Management

### Lava Worker Auto Scaling

Lava workers created using the provided worker CloudFormation template sit in an
auto scaling group with a set of supporting resources to assist with horizontal
capacity scaling and controlled worker node termination.

The auto scaling architecture is shown below.

![](img/lava-worker-scaling.svg)

The key components are:

1.  The EC2 auto scaling group itself, named `lava-<REALM>-<WORKER>`.    
    The *minimum*, *preferred* and *maximum* instance counts are specified as
    parameters in the worker CloudFormation stack. Workers that act as schedule
    based dispatchers **must** have all values set to 1. Other workers can have
    whatever is needed noting that the auto scaling can create that many
    instances, so be reasonable. Also note that if auto scaling is enabled, the
    minimum should be 1 or the auto scaler will scale down to 0 and it will
    never scale up.

2.  A lambda function, `lava-<REALM>-metrics`.    
    This is triggered by an Amazon EventBridge schedule every minute to generate
    a metric that is the worker *SQS job queue depth per in-service instance* in
    the auto scaling group. This metric is used to drive the auto scaling
    process using a *TargetTracking* policy.  This is referred to as the
    **worker backlog**.

3.  An EC2 auto scaling *TargetTracking* policy.    
    This is controlled by the worker backlog metric to cause the worker fleet to
    scale out or in as appropriate. The target value for auto scaling purposes
    is specified in the worker CloudFormation stack. See [Setting the Auto
    Scaling Target
    Value](#setting-the-auto-scaling-target-value).

4.  An EC2 auto scaling lifecycle hook for terminating nodes.    
    This will send an appropriate message to the Amazon EventBridge default bus.

5.  An AWS EventBridge rule, `lava-<REALM>-<WORKER>-terminating`.    
    This detects the lifecycle hook message and triggers the `lava-<REALM>-stop`
    lambda function, providing it with the lifecycle event details.

6.  The `lava-<REALM>-stop` lambda function.    
    This uses AWS Systems Manager `RunCommand` to run the
    [lava-stop](#lava-stop-utility)
    utility on the instance. This will do a controlled shutdown of the lava
    worker daemons and wait for them to complete. It also inhibits further
    scheduled job dispatches during the shutdown process. Auto scaling
    lifecycle hook heartbeat messages will be issued periodically until the 
    daemons stop, at which point a lifecycle completion message will be sent.
    If the daemons fail to stop in a reasonable period of time, they are killed.
    
#### Setting the Auto Scaling Target Value

The lava worker EC2 auto scaling process uses a *TargetTracking* policy based
on a custom metric referred to as the **worker backlog**. This is defined as
the `ApproximateNumberOfMessagesVisible` for the worker job queue divided by the
number of instances in the `InService` state in the work auto scaling group.

In short, the **worker backlog** is the number of jobs waiting per worker
instance.

This follows the pattern
[recommended by AWS](https://docs.aws.amazon.com/autoscaling/ec2/userguide/as-using-sqs-queue.html).

The metric is calculated every minute by the `lava-<REALM>-metrics` lambda function.

|Metric Name|Namespace|Dimensions|Unit|
|-|-|-|-|
|WorkerBacklog|Lava|Realm, Worker|None|

The crucial aspect of the auto scaling process is the selection of the target
value for the `WorkerBacklog` metric.

#### Method 1 - AWS Recommended Approach

To do this, AWS recommends the following [process](https://docs.aws.amazon.com/autoscaling/ec2/userguide/as-using-sqs-queue.html#scale-sqs-queue-custom-metric):
 
1.  Estimate the acceptable latency for a job to run.

2.  Estimated the average processing time (i.e. average job run time).

3.  Divide the latency by the average run time to get the target value.

For example, if the acceptable latency is 10 minutes (600 seconds) and the
average job run time is 20 seconds, the target value would be 30. So if the
queue gets 300 messages, it will start 10 instances. This may, or may not, be what
you want to happen.

!!! note
    The number of worker instances is always capped by the maximum instance
    count of the auto scaling group, as specified in the lava worker
    CloudFormation stack.

#### Method 2 - Guess

The trouble with method 1 is that lava jobs can vary widely in run time, from
seconds to hours. So the average processing time may not be a reliable data
point.

An alternative approach is to disable auto scaling initially (using parameters
in the worker CloudFormation stack) and monitor the SQS queue depth for a period
of time. Then take an educated guess.

!!! tip
    It's probably better to set the target too high rather than too low,
    initially.

### Stopping the Worker Daemon

As of version 5.1.0 (Tungurahua), the preferred mechanism to stop the worker
daemon is to send it one of the following signals to initiate a controlled
shutdown:

*   SIGHUP (signal number 1)
*   SIGINT (signal number 2)

The worker will complete any in-flight jobs before terminating.

A second signal will cause a hard shutdown, causing in-flight jobs to be
terminated and, possibly, resubmitted by SQS once the queue visibility timeout
expires.

### AWS Systems Manager Support

As of lava version 6.2.0 (Reventador), a number AWS Systems Manager command
documents are provided to assist with performing operations on EC2 based worker
nodes. These are deployed as part of the
[lava-common.cfn.json](#building-the-cloudformation-templates) CloudFormation stack.

#### lava-RebootWorkerInstance

This command document performs the following steps:

1.  Perform a yum security update.

2.  Stop any further scheduled dispatches from the instance.

3.  Perform a controlled stop of any lava worker daemons.

4.  Reboot the instance.

When the instance reboots, the dispatch blockage will be removed and the worker
daemons will be restarted.

#### lava-SecurityUpdate

This command document is a more sophisticated version of
[lava-RebootWorkerInstance](#lava-rebootworkerinstance) designed specifically to
perform yum security updates. It is less disruptive in that it will not reboot
a worker instance unless it is necessary.

It performs the following steps:

1.  Check if the instance has been up for at least a specified period of time.

2.  Check if any security updates are pending. If not, exit.

3.  Apply the security updates with `yum update --security`.

4.  Check if a reboot is required. If not, exit.

5.  Signal the worker daemons to stop.

6.  Wait a specified period of time for the worker daemons to finish any
    in-flight jobs and stop.

7.  Kill any worker daemons still running.

8.  Reboot the instance.

The command document accepts the following parameters:

|Parameter|Default|Description|
|-||---------|
|ExecutionTimeout|`3600`|Execution timeout in seconds. The `ExecutionTimeout` must exceed the `Wait` duration by enough to allow the patching activity and a reboot.|
|LogLevel|`info`|Logging level. Allowed values are `debug`, `info`, `warning`.|
|MinUpDays|`0`|Skip the update process if the EC2 instance hasn't been up for this many days.|
|Signal|`SIGHUP`|Signal the worker to stop (if necessary) with the specified signal. Allowed values are `SIGHUP` and `SIGKILL`. See [Stopping the Worker Daemon](#stopping-the-worker-daemon).|
|Wait|`15m`|Wait for the specified duration for lava workers to stop voluntarily before killing them. |

The command document sends status messages to Amazon EventBridge as part of the
process. These can be captured using standard EventBridge mechanisms to send
notifications to system operators or trigger other automated action, as required.
The messages look like this:

```json
{
  "version": "0",
  "id": "a1ce8e44-dada-d265-2b9e-beed76ab493b",
  "detail-type": "Lava Worker Instance Patching Notification",
  "source": "lava",
  "account": "123456789123",
  "time": "2023-05-20T08:16:36Z",
  "region": "ap-southeast-2",
  "resources": [],
  "detail": {
    "instance-id": "i-082cafe1b7811a47a",
    "instance-name": "lava-dev0-core",
    "info": "Rebooting after security patching"
  }
}
```

```json
{
  "version": "0",
  "id": "79d96f65-1be1-50b4-fd4c-d0ae39981eb7",
  "detail-type": "Lava Worker Instance Patching Notification",
  "source": "lava",
  "account": "123456789123",
  "time": "2023-05-20T08:18:00Z",
  "region": "ap-southeast-2",
  "resources": [],
  "detail": {
    "instance-id": "i-082cafe1b7811a47a",
    "instance-name": "lava-dev0-core",
    "info": "Reboot complete"
  }
}

```

#### lava-StopWorkerDaemons

This command document performs the following steps:

1.  Optionally, stop any further scheduled dispatches from the instance.

2.  Perform a controlled stop of any lava worker daemons.

The instance is not rebooted. Further action (e.g. to restart lava worker
daemons and re-enable dispatches) requires operator intervention.

### Security Patching of Lava EC2 Workers { data-toc-label="Security Patching of EC2 Workers" }

The [lava-SecurityUpdate](#lava-securityupdate) SSM command document provides a
convenient mechanism to perform controlled security updates on EC2 based
lava workers.

This command document can be scheduled by lava itself via a standard job. The
following example shows how this can be done for a given target realm (which
can be different from the realm initiating the command).


```json
{
  "description": "Security patching for lava nodes",
  "dispatcher": "Sydney",
  "enabled": true,
  "job_id": "lava/admin/secupdate/<REALM>",
  "owner": "Deus ex machina",
  "parameters": {
    "vars": {
      "realm": "dev",
      "up_days": 7,
      "wait_mins": 60
    }
  },
  "payload": "aws ssm send-command --document-name \"lava-SecurityUpdate\" --targets '[{\"Key\":\"tag:LavaRealm\",\"Values\":[\"{{vars.realm}}\"]}]' --parameters '{\"Wait\":[\"{{vars.wait_mins}}m\"],\"MinUpDays\":[\"{{vars.up_days}}\"],\"ExecutionTimeout\":[\"{{(vars.wait_mins+15)*60}}\"]}' --cloud-watch-output-config '{\"CloudWatchOutputEnabled\":true,\"CloudWatchLogGroupName\":\"lava\"}'",
  "schedule": "0 19 * * Sat,Sun",
  "type": "cmd",
  "worker": "core"
}

```

The IAM setup for this to work requires that the lava worker can run
`ssm:SendCommand` for

*   The `lava-*` command documents; and
*   For all EC2 instances with specified values of the `LavaRealm` tag.

The IAM policy for the worker will include elements like these:

```json
{
  "Sid": "RunLavaCommandDocs",
  "Action": "ssm:SendCommand",
  "Effect": "Allow",
  "Resource": [
    "arn:aws:ssm:ap-southeast-2:123456789123:document/lava-*"
  ]
},
{
  "Sid": "RunLavaCommandInstances",
  "Action": "ssm:SendCommand",
  "Condition": {
    "StringLike": {
      "ssm:resourceTag/LavaRealm": "*"
    }
  },
  "Effect": "Allow",
  "Resource": [
    "arn:aws:ec2:*:*:instance/*"
  ]
},
```
