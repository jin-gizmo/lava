
## Action type: state

The **state** action type allows jobs to post [state items](#the-lava-state-manager)
that can be subsequently retrieved by other jobs or authorised external actors.

|Field|Type|Required|Description|
|-|-|-|-------------------------------------------------------------|
|action|String|Yes|The action type: `state`.|
|kms_key|String|No|The [secure](#state-item-types) state item type supports KMS encryption of the value. This field specifies the KMS key to use, either as a KMS key ARN or a key alias in the form `alias/key-id`. Defaults to the `sys` key for the lava realm. Ignored for other state item types.|
|publisher|String|No|An arbitrary identifier for the entity posting the event item. Not used by lava itself. The default is the job ID. This is Jinja rendered prior to use.|
|state_id|String|Yes|The state entry ID. This is Jinja rendered prior to use.|
|ttl|String|No|Time to live for the state item specified as a duration in the form `nnX` where `nn` is a number and `X` is `s` (seconds), `m` (minutes), `h` (hours) or `d` (days). If greater than the [maximum specified for the realm](#lava-worker-configuration), it will be silently reduced to that value. A [default value](#lava-worker-configuration) is provided by lava which can be overridden at the realm level.|
|type|String|No|The [state item type](#state-item-types). If not specified, the `json` type is used.|
|value|\*|Yes|A JSON encodable object. This is Jinja rendered prior to use.|

!!! info
    Do not create state items with a `state_id` starting with `lava`.
    This prefix is reserved.

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
