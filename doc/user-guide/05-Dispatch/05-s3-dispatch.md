
## Dispatching Jobs from S3 Events

Lava jobs can be dispatched in response to S3 events. This is done using a realm
specific Lambda function **s3trigger** which, optionally, gets deployed as a
function named `lava-<REALM>-s3trigger` when the main realm CloudFormation stack
is deployed.

S3 event messages can be sent to the **s3trigger** lambda as either:

*   S3 bucket notification events delivered directly from S3, via SNS or via
    SQS.

*   [Amazon EventBridge](https://docs.aws.amazon.com/AmazonS3/latest/userguide/EventBridge.html)
    messages.

The following diagram shows the various event notification options supported by
lava.

![](img/s3trigger.svg)

Note that the CloudFormation stack will deploy the function, the [s3triggers
table](#the-s3triggers-table) and required IAM components but
it will not add any entries in the [s3triggers
table](#the-s3triggers-table), nor will it add any S3
subscriptions to the lambda function. These steps must be done manually.

The s3trigger function works thus:

1.  An S3 bucket notification event or Amazon EventBridge event record is passed
    to the Lambda function.

2.  The function looks up the [s3triggers table](#the-s3triggers-table)
    to find entries that match the bucket name and object key. There may be
    multiple matching entries.

3.  If there is no matching s3triggers entry, the final path component of the
    prefix is removed and the search for matching entries is repeated. This
    process is repeated until either an entry is found, or all path components
    have been exhausted.

4.  Any matching s3trigger entries with the `enabled` field set to `false` are
    discarded.

5.  For each remaining s3trigger entry, any `if_*` and `if_not_*` conditions are
    evaluated. If these checks pass, the job referenced in the s3trigger entry
    is dispatched.

!!! info
    Like lava jobs, s3trigger entries must be explicitly enabled in order to be
    active.

For example, if the bucket name is `mybucket` and the object key for the S3
event notification is `a/b/c`, the  [s3triggers
table](#the-s3triggers-table) will be progressively queried for
the following table entries until one is found.

*   bucket=`mybucket`, prefix=`a/b/c`
*   bucket=`mybucket`, prefix=`a/b`
*   bucket=`mybucket`, prefix=`a`
*   bucket=`mybucket`, prefix=`*`

The final query refers to an s3triggers entry for the entire bucket (i.e. an
empty prefix). This use of `*` to represent an empty prefix is a consequence of
DynamoDB's inability to handle empty strings.

!!! note
    DynamoDB has now been updated to handle empty strings but lava retains the
    requirement to use a `*` as described above.

Query results are cached for a short period of time to reduce traffic on the
[s3triggers](#the-s3triggers-table) and
[jobs](#the-jobs-table) tables. The cache duration can be
modified by setting the
[S3TRIGGER_CACHE_TTL](#configuration-for-s3trigger)
configuration variable. The scope of the cache is limited to each run-time
instance of the lambda function. This works because AWS Lambda will reuse
run-time instances where possible.

### Rendering of Dispatch Parameters { data-toc-label="Rendering Dispatch Parameters" }

The s3trigger entry contains the job\_id for the job to be dispatched and may
also contain a map of parameters for the job and a map of globals that will be
included in the dispatch.

These parameters and globals will be rendered using
[Jinja](http://jinja.pocoo.org) unless the s3trigger entry has a `jinja` field
set to `false`. This rendering process allows information related to the S3
event, such as the bucket name and object key, to be passed to the lava job at
run time.

The parameters must be legal values for the job type being dispatched. They will
be merged in with any parameters in the job specification itself.

The globals are agnostic of job type and can be provided to any job. They will
be merged in with any globals in the job specification itself and made available
to the Jinja rendering process of any job that uses this mechanism.

The following variables are made available to the renderer.

|Name|Type|Description|
|-|-|-------------------------------------------------------------|
|bucket|str|The bucket name.|
|key|str|The S3 object key.|
|event|dict[str,\*]|The raw S3 event record. The format of this can vary significantly, depending on whether the event message was delivered directly from S3 or via SQS, SNS or EventBridge. Don't use it unless absolutely necessary.|
|info|dict[str,\*]|A canonical extract of the most useful elements from the S3 event record. It is consistent in structure and content across the different event record delivery mechanisms and should be used instead of `event`.  Normal Jinja syntax can be used to extract components of interest. A sample is shown below.|
|utils|dict[str,runnable]|A dictionary of [utility functions](#jinja-utility-functions) that can be used in the Jinja markup.|

The `info` object contains the following elements:

|Name|Type|Description|
|-|-|-------------------------------------------------------------|
|aws\_region|str| The AWS region for the S3 operation.|
|bucket|str|The bucket name.|
|event\_time|datetime|A timezone aware datetime for the S3 operation.|
|event\_type|str|The type of S3 operation that caused the event. See [About S3 Event Types](#about-s3-event-types) below.|
|key|str|The S3 object key.|
|size|int|The size in bytes of the object.|
|source\_ip|IPv4Address \| IPv6Address|The source IP address of the S3 operation. See [ipaddress](https://docs.python.org/3/library/ipaddress.html) in the Python standard library documentation.|


A typical `info` (Python) object looks like this:


```python
{
    'bucket': 'my-bucket',
    'key': 'HappyFace.jpg',
    'size': 1024,
    'event_time': datetime.datetime(2022, 1, 30, 16, 18, 17, 123, tzinfo=tzutc()),
    'source_ip': IPv4Address('10.200.240.5'),
	'event_type': 'ObjectCreated:Put',
	'aws_region': 'ap-southeast-2'
}

```

An s3triggers (JSON) entry may then look like this.

```json
{
    "description": "Something interesting just happened.",
    "bucket": "...",
    "prefix": "...",
    "enabled": true,
    "globals": {
        "bucket": "{{bucket}}",
        "key": "{{key}}",
        "account-id": "{{bucket.split(':')[4]}}"
    },
    "if_fnmatch": "*.zip",
    "if_not_fnmatch": "*ignore*",
    "if_size_gt": 0,
    "job_id": "my_exe_job",
    "parameters": {
        "env": {
            "BUCKET": "{{bucket}}",
            "KEY": "{{key}}",
            "IP": "{{info.source_ip}}",
            "EVENT_TIME": "{{info.event_time.isoformat()}}"
            }
        },
    "trigger_id": "unique_trigger_id"
}
```

### About S3 Event Types

AWS is very inconsistent in values for event types between EventBridge
messages and the S3 bucket notification configuration mechanisms. Lava can't
easily fix that without compounding the problem. Sorry.

For example, when an S3 object is created, the S3 bucket notification
configuration event will have an `eventName` field something like
`ObjectCreated:Put`. The EventBridge message for the same action will have a
`detail-type` field of `Object Created` and a `detail.reason` value of
`PutObject`. The other S3 event types vary even more than this.

!!! note
    This is spectacularly unnecessary and annoying. The only saving grace is that
    it's rarely necessary to use this field in lava. Filtering can be done by the
    AWS service itself in most cases (S3 or EventBridge).

This is how lava populates the `info.event_type` value when Jinja rendering an
s3trigger specification:

|Source|Value for event\_type|
|----|-|
|S3|The `eventName` field is used as-is.|
|EventBridge|The `detail-type` and `detail.reason` fields are joined with a colon and all whitespace removed. e.g. Putting a file in S3 will yield `ObjectCreated:PutObject`.|

See the
[EventBridge message structure](https://docs.aws.amazon.com/AmazonS3/latest/userguide/ev-events.html)
documentation for more information.

### S3 Event Deduplication

AWS does not guarantee that an individual S3 event will generate a single event
notification. Duplicate event messages are *very* rare, except when AWS S3
bucket replication is configured which seems to generate multiple event
notifications more often.

Duplicate event notifications tend to occur within a small number of seconds of
each other and can cause problems for lava jobs as two instances of a job
operating on the same S3 object will be dispatched at almost the same time.

The lava s3trigger lambda provides a level of support for reducing the risk of
message duplication by, optionally, caching S3 object data for received
notifications and discarding duplicates. The following attributes are compared
to determine if an event notification is a duplicate:

*   bucket name

*   object key

*   object size

*   event type.

The effectiveness of this mechanism is pretty good but it is limited by these
factors:

*   The cache is time limited.

*   The cache is size limited.

*   As the cache is within the lambda itself, it relies on duplicate messages
    being received by the same warm invocation instance of the s3trigger lambda.

The caching process is disabled by default and the cache configuration is
configurable via the
[S3TRIGGER_DEDUP_CACHE_SIZE](#configuration-for-s3trigger)
and
[S3TRIGGER_DEDUP_TTL](#configuration-for-s3trigger)
parameters.

If a more robust deduplication mechanism is required, it needs to be implemented
outside lava (e.g. using a FIFO SQS queue to feed messages to s3trigger).

!!! warning
    Be aware that the *duplicate* S3 event messages can have different message
    ID fields so some external logic would be required to explicitly set the SQS
    message deduplication ID if a FIFO queue is used. Are we having fun yet?


### Testing S3 Triggers

Testing an S3 trigger requires that the s3trigger Lambda function is invoked
with a well-formed AWS S3 bucket notification event. There are essentially three
ways to do this:

1.  Configure S3 or EventBridge to send the notifications appropriately and then
    drop the object of interest in S3. Repeating the test involves copying the
    object back on top of itself.

    While this will work fine, it can be cumbersome to do manually, particularly
    if multiple objects are involved. It can also have unintended side effects
    if it triggers other unrelated actions.

2.  Construct an Amazon EventBridge message in the appropriate format and use the
    AWS CLI to submit the message on the default event bus.

3.  Generate artificial bucket notification events and use those to invoke the
    lambda directly.

    Lava comes with a simple shell script `etc/s3lambda.sh` to do this. Run
    `etc/s3lambda.sh -h` to get help.
    
### Configuring S3 Bucket Notification Events { data-toc-label="Configuring S3 Events" }

The s3trigger lambda function can receive S3 bucket notification events via any
of the following mechanisms:

1.  Direct subscription of the lambda function to the source bucket.
    
2.  Via SQS, where the source bucket has been configured to send event
    notifications to an SQS queue.
    
3.  Via SNS, where the source bucket has been configured to send event
    notifications to an SNS topic.

!!! tip
    In each case, it is strongly recommended to configure the trigger from the
    AWS Lambda console, not from the SNS/SQS/S3 console to avoid arcane IAM
    permission issues.

### Configuring Amazon EventBridge for S3 Events { data-toc-label="Configuring EventBridge for S3 Events" }

The process is basically this:

1.  Configure the bucket to send notifications to Amazon EventBridge for all
    events. All events on that bucket will be sent to the default event bus.

2.  Create a rule on the default event bus to capture events of interest.
    *   The rule name **must** be in the form `lava.<REALM>.*`.
    *   The event pattern should select S3 objects of interest.
    *   The target list must include the lambda `lava-<REALM>-s3trigger`.
    *   The rule input (i.e. what gets sent to the lambda) must be set to
        **Matched event**.

An event pattern will look something like this:

```json
{
	"source": ["aws.s3"],
	"detail-type": ["Object Created"],
	"detail": {
		"bucket": {
			"name": ["my-bucket"]
		},
		"object": {
			"key": [
                { "prefix": "an-interesting-prefix" }
            ]
		}
	}
}
```

!!! tip
    The [lava job framework](#creating-amazon-eventbridge-rules) provides
    built-in support for creating EventBridge rules suitable for triggering jobs
    from S3 events.

More information:

*   [Amazon S3 Event Notifications using EventBridge](https://docs.aws.amazon.com/AmazonS3/latest/userguide/EventBridge.html)

*   [Amazon EventBridge event patterns](https://docs.aws.amazon.com/eventbridge/latest/userguide/eb-event-patterns.html)
