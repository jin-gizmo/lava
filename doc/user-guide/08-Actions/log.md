
## Action type: log

The **log** action type writes a message to the logger local to the worker with
log level `info`. The worker log configuration is specified as command line
arguments so it depends on these where the message ends up.

For more information on worker logging arguments run:

```bash
lava-worker --help
```

|Field|Type|Required|Description|
|-|-|-|-------------------------------------------------------------|
|action|String|Yes|The action type: `log`.|
|message|String|Yes|The message to log. This is Jinja rendered.|

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
