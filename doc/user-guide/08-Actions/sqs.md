
## Action type: sqs

The **sqs** action type sends a message to an SQS queue.

|Field|Type|Required|Description|
|-|-|-|-------------------------------------------------------------|
|action|String|Yes|The action type: `sqs`.|
|dedup_id|String|No|The token used for deduplication of sent messages. This parameter applies only to FIFO queues. This is Jinja rendered.|
|delay|String|No|Message sending delay in the form `nnX` where `nn` is a number and `X` is `s` (seconds) or `m` (minutes). The maximum allowed value is 15 minutes.|
|group_id|String|No|The tag that specifies that a message belongs to a specific message group. This parameter applies only to FIFO queues. This is Jinja rendered.|
|message|String _or_  Map[String,\*]|Yes|The message body. This can be either a string or an object. If it is an object it will be JSON encoded before sending. This is Jinja rendered.|
|queue|String|Yes|The name or URL of the queue (not the ARN!).|

The Jinja rendered action parameters have the following variables injected.

|Name|Type|Description|
|-|-|-------------------------------------------------------------|
|globals|dict[str,\*]|The globals map for the job that triggered the action.|
|job|dict[str,\*]|The [augmented job specification](#the-augmented-job-specification) for the job that triggered the action.|
|realm|dict[str,\*]|The realm specification.|
|result|dict[str,\*]|The result object from the job that triggered the action.|
|start|datetime|The local time when the job run started.|
|state|dict[str,\*]|A dictionary of the state items imported into the job, keyed on state_id. The default values are updated at run-time with any current values obtainable from the [state](#the-state-table) table.|
|ustart|datetime|The UTC time when the job run started.|
|utils|dict[str,runnable]|A dictionary of [utility functions](#jinja-utility-functions) that can be used in the Jinja markup.|

Refer to [Jinja Rendering in Lava](#jinja-rendering-in-lava)
for more information.

This is an example of how a JSON formatted object can be sent:

```jsomn
{
    "on_success" : [
        {
            "action": "sqs",
            "message": {
                "key1": "Hello world",
                "key2": {
                    "key2a": "{{ job.globals.a_global }}",
                    "key2b": 42
                }
            },
            "topic": "myqueue"
        }
    ]
}
```
