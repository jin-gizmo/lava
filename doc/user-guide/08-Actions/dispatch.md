
## Action type: dispatch

The **dispatch** action type dispatches another lava job.

Any globals available in the job that triggers the action will also be passed in
the dispatch request to the job being dispatched.

|Field|Type|Required|Description|
|-|-|-|-------------------------------------------------------------|
|action|String|Yes|The action type: `dispatch`.|
|delay|String|No|Dispatch message sending delay in the form `nnX` where `nn` is a number and `X` is `s` (seconds) or `m` (minutes). The maximum allowed value is 15 minutes.|
|job\_id|String|Yes|The job to be dispatched. This is Jinja rendered prior to use.|
|parameters|Map[String,\*]|No|A map of parameters that will be sent with the dispatch. These are Jinja rendered prior to use. The dispatched job will receive these in the `parameters` element of its job specification.|

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
