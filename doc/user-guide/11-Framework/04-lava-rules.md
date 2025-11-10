
## Creating Amazon EventBridge Rules { data-toc-label="Creating EventBridge Rules" }

Lava provides support for triggering jobs from Amazon EventBridge rules via a
number of mechanisms:

*   Using the [lava dispatch helper](#dispatching-jobs-from-amazon-eventbridge).

*   Using Amazon S3 Event Notifications with Amazon EventBridge.

Also, a project may need to create EventBridge rules to interact with other
non-lava elements in the environment.

In each case, EventBridge rules with suitable targets need to be created. The
lava job framework supports this with rule specifications placed in the
`lava-rules` directory.

> Sorry, I couldn't resist.

### Anatomy of EventBridge Rules

!!! note
    This explanation is for general information only and many details are omitted.
    Consult AWS documentation for full details.

EventBridge rules are attached to an event bus (typically the `default` bus) and
contain the following key components:

*   A rule name.

*   A description.

*   An optional event pattern that is matched against incoming events by
    EventBridge at runtime to determine if the rule should fire or not.

*   An optional schedule that specifies a *cron* style schedule or repetition
    frequency for the rule to fire.

*   Targets for the rule and a definition of what data to send to the targets.
    A range of target types are supported, including Lambda functions, 
    CloudWatch log groups, SNS topics and SQS queues. While targets are optional,
    not having any is pretty pointless.

*   Tags for the rule.

For the lava job framework, these elements are defined in a [rule specification
file](#rule-specification-files).

### Rule Specification Files

Rule specification files are YAML (or JSON, if you must) formatted and placed in
the `lava-rules` directory. These files are Jinja rendered against the specified
environment configuration file as for other YAML job framework components and
deployed to EventBridge by the lava job framework.

A sample rule specification file is provided [here](#rule-samples).

Each file has the following keys:

|Key|Type|Required|Description|
|-|-|-|-------------------------------------------------------------|
|description|str|Yes|A short description of the rule.|
|enabled|Boolean|No|Whether or not the rule is enabled. Defaults to `false`|
|event_bus_name|str|No|The event bus name. The default is `default`.|
|event_pattern|dict|No|The pattern used to select which events trigger the rule. See the [AWS documentation](https://docs.aws.amazon.com/eventbridge/latest/userguide/eb-event-patterns.html) for details.|
|owner|str|Yes|Name or email address of the rule owner. This will be added as a tag on the rule when deployed.|
|role_arn|str|No|The ARN of the IAM role associated with the rule. See the [AWS documentation](https://docs.aws.amazon.com/eventbridge/latest/userguide/eb-manage-iam-access.html) for details.|
|rule\_id|str|Yes|The rule name. This must be of the form `lava.<REALM>.*`.|
|schedule_expression|str|No|A *cron* style schedule or repetition frequency for the rule to fire. See the [AWS documentation](https://docs.aws.amazon.com/eventbridge/latest/userguide/eb-create-rule-schedule.html) for details.|
|tags|dict|No|A dictionary of key/value pairs that will be added as tags to the rule. These are additional to the `owner` and control tags added by the lava framework.|
|targets|list|No|A list of targets for the rule. If omitted, the rule may fire but nothing will happen. See [Specifying Rule Targets](#specifying-rule-targets).|

### Specifying Rule Targets

A rule target is a resource to which EventBridge sends an event message when a
rule fires. Rules can have zero or more targets. Consult the
[AWS documentation](https://docs.aws.amazon.com/eventbridge/latest/userguide/eb-targets.html)
for details.

[Rule specification files](#rule-specification-files) may contain the `targets`
key which is a list of targets for the rule. Each entry in the list specifies
the resource or endpoint and any additional parameters required for that
endpoint.

The format for each entry in the `targets` list can be either:

1.  The ARN of a target resource.

2.  A full target specification using the structure specified for a target in
    the boto3 EventBridge
    [put_targets](https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/events.html#EventBridge.Client.put_targets)
    function (camel case and all). 

In the first case, the incoming event is forwarded, unmodified, to the resource
specified by the ARN. This is suitable for
[using EventBridge to trigger lava jobs from S3 events](#configuring-amazon-eventbridge-for-s3-events),
among other uses. The lava job framework provides 
[Jinja helper functions](#built-in-rendering-variables) to assist with
constructing ARNs.

In the second case, the specification provides full control over the target
configuration, including the nature of the event message being sent.


### Example Rule Specification File { data-toc-label="Example" }

The following example is typical of one used to send an S3 bucket event to the
realm s3trigger lambda function to dispatch a lava job. It also logs the event
to CloudWatch logs.

```yaml
# rule_id becomes the rule name
rule_id: "<{ prefix.rule }>.s3-rule-example"

# If you forget this, your rule is disabled.
enabled: true

owner: Fred
description: A sample rule

tags:
  project: my-great-project

# This will capture object creation in s3://my-bucket/an/interesting/prefix
event_pattern:
  detail:
    bucket:
      name:
        - my-bucket
    object:
      key:
        - prefix: an/interesting/prefix
  detail-type:
    - Object Created
  source:
    - aws.s3

targets:

  # Construct the ARN for the realm s3trigger lambda
  - <{ lava.aws.arn('lambda-function', 'lava-' + realm + '-s3trigger') }>
  # Let's log messages in CloudWatch logs
  - <{ lava.aws.arn('log-group', '/aws/events/lava') }>

  # This does exactly the same as the previous targets using the full target
  # format. Don't do both or s3trigger will get 2 events sent
  - Id: trigger-me
    Arn: <{ lava.aws.arn('lambda-function', 'lava-' + realm + '-s3trigger') }>
  - Id: log-me
    Arn: <{ lava.aws.arn('log-group', '/aws/events/lava') }>

```

