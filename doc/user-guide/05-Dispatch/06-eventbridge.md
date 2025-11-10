
## Dispatching Jobs from Amazon EventBridge { data-toc-label="Dispatching from EventBridge" }

[Amazon EventBridge](https://aws.amazon.com/eventbridge/) is an increasingly
pervasive event management and distribution tool within AWS environments. It
gathers events from a number of sources, selects events of interest based on
user defined criteria and sends those events to one or more targets for response
/ processing.

Events in an EventBridge event bus can be used to trigger the dispatch of lava
jobs using the [lava dispatch helper](#the-dispatch-helper).

The [lava dispatch helper](#the-dispatch-helper) is a lambda
function that that can receive dispatch requests via SQS and SNS. It can also
handle appropriately formatted dispatch requests sent from EventBridge directly
to the dispatch helper lambda function.

The manual setup process is:

1.  Go to the Amazon EventBridge console and create a new event rule.

2.  Fill in the event pattern / event bus settings as required.

3.  Under **Select Targets**, select the realm dispatch lambda function and
    enable **Input Transformer**. This requires specification of an
    **Input Path** and an **Input Template**.

4.  The **Input Path** selects fields from incoming event messages and makes
    them available for injection into the message sent to the dispatch helper
    lambda function. Use it to select whatever fields from the input event are
    needed in the lava dispatch request.

5.  The **Input Template** is the message that actually gets sent to the
    dispatch lambda. The message must be a JSON formatted object that complies
    with the [JSON dispatch request format](#json-dispatch-requests).

This process is automated when EventBridge rules are created using the
[lava job framework](#creating-amazon-eventbridge-rules).

### Example

As an example, consider a requirement to dispatch a lava job in response to an
AWS EC2 auto scaling event, with the EC2 instance ID and auto scaling group name
passed as globals to the lava job.

The auto scaling event message in the event bus looks like this:

```json
{
  "version": "0",
  "id": "...",
  "detail-type": "EC2 Instance Launch Successful",
  "source": "aws.autoscaling",
  "account": "123456789012",
  "time": "2020-10-11T11:23:51Z",
  "region": "ap-southeast-2",
  "resources": [
    "arn:aws:autoscaling:ap-southeast2:123456789012:autoScalingGroup:...",
    "arn:aws:ec2:ap-southeast-2:123456789012:instance/i-0cefe067f7c6ee173"
  ],
  "detail": {
    "StatusCode": "InProgress",
    "AutoScalingGroupName": "myAutoScalingGroup",
    "ActivityId": "...",
    "Details": {
      "Availability Zone": "ap-southeast-2a",
      "Subnet ID": "subnet-745bae91"
    },
    "RequestId": "...",
    "EndTime": "2020-10-11T11:23:51Z",
    "EC2InstanceId": "i-0cefe067f7c6ee173",
    "StartTime": "2020-10-11T11:16:43Z",
    "Cause": "..."
  }
}
```

As the lava job requires the name of the auto scaling group and the
affected EC2 instance ID as job globals, the **Input Path** would look like
this:

```json
{
  "asg_name": "$.detail.AutoScalingGroupName",
  "instance": "$.detail.EC2InstanceId"
}
```

The **Input Template** uses `<input_path_var>` to select values from the **Input
Path**. The **Input Template** that constructs the dispatch request looks like
this:

```json
{
  "job_id": "my-job-id",
  "globals": {
      "instance": "<instance>",
      "asg_name": "<asg_name>"
  }
}
```

### Testing EventBridge Dispatch

Testing of the configuration involves EventBridge receiving and processing an
event that meets the selection criteria for the event rule. If it is not easy to
have this occur naturally, it is straightforward to hand-craft a message and use
the AWS CLI to send it.

First create a JSON formatted file (e.g. `events.json`) containing the event(s).
This only requires enough details to meet the EventBridge rule filtering
criteria and to support the information required to create the message for the
target.

For example:

```json
[
  {
    "Source": "...",
    "Detail": "{ \"AutoScalingGroupName\": \"...\", \"EC2InstanceId\": \"...\" }",
    "Resources": [
      "resource1",
      "resource2"
    ],
    "DetailType": "myDetailType"
  }
]
```

Note that `Detail` is a string containing a JSON encoded object.  Send the
message, thus:

```bash
aws events put-events --entries file://events.json
```
