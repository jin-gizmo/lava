
## Action type: event

The **event** action type sends an event to AWS EventBridge.

|Field|Type|Required|Description|
|-|-|-|-------------------------------------------------------------|
|action|String|Yes|The action type: `event`.|
|detail_type|String|No|The event detail type. This is Jinja rendered prior to use. Defaults to `Lava Job Action`.|
|detail|String _or_ Map[String,\*]|No|Event detail. The string, or the map values, are Jinja rendered prior to use. Defaults to a map containing realm, worker, job_id, run_id and exit_status.|
|event_bus|String|No|The event bus name. This is Jinja rendered prior to use. Defaults to the default event bus.|
|resources|List[String]|No|A list of resources. This is Jinja rendered prior to use. Defaults to an empty list.|
|source|String|No|The event source. This is Jinja rendered prior to use. Defaults to `lava.<REALM>`.|

!!! info
    The [realm CloudFormation template](#the-lava-realm-cloudformation-template)
    only provides workers with permission to put events on the default event bus.

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

This is the minimal action specification:

```json
{
    "on_success": [
        {
            "action": "event"
        }
    ]
}
```

It will produce an event in the default event bus like so:

```json
{
  "version": "0",
  "id": "1bdf1ead-95ef-79fd-1342-8f8ff1e57765",
  "detail-type": "Lava Job Action",
  "source": "lava.dev",
  "account": "123456789012",
  "time": "2021-07-25T05:12:23Z",
  "region": "ap-southeast-2",
  "resources": [],
  "detail": {
    "realm": "dev",
    "worker": "core",
    "job_id": "action/event/default",
    "run_id": "05175b7c-8b0d-40ed-af31-0bc846bbe400",
    "exit_status": 0
  }
}
```

This is a sample, custom event:

```json
{
    "on_success": [
        {
            "action": "event",
            "detail": {
                "job_id": "{{ job.job_id }}",
                "realm": "{{ realm.realm }}",
                "result": "{{result | tojson}}",
                "run_id": "{{job.run_id }}",
                "status": "success"
            }
        }
    ]
}
```
