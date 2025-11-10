
## Action type: slack

The **slack** action sends a message to a Slack channel. It relies on
the [slack connector](#connector-type-slack) which uses
[Slack webhooks](https://api.slack.com/messaging/webhooks).

|Field|Type|Required|Description|
|-|-|-|-------------------------------------------------------------|
|action|String|Yes|The action type: `slack`.|
|colour|String|No|As per the `colour`  field of the [slack connector](#connector-type-slack). If not specified, the value specified in the connector is used.|
|from|String|No|An arbitrary source identifier for display in the Slack message. If not specified, any default value specified in the connector will be used.|
|message|String|Yes|The message body. This is Jinja rendered prior to use. Only the first 3,000 characters of the rendered value are used.|
|preamble|String|No|As per the `preamble`  field of the [slack connector](#connector-type-slack). If not specified, the value specified in the connector is used.|
|slack\_conn|String|Yes|The name of a [slack](#connector-type-slack) connector to use.|
|style|String|No|As per the `style`  field of the [slack connector](#connector-type-slack). If not specified, the value specified in the connector is used.|
|subject|String|No|The message subject. This is Jinja rendered prior to use. Only the first 250 characters of the rendered value are used.|

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

