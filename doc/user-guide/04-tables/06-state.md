
## The State Table { data-toc-label="State" }

The state table for a given `<REALM>` is named `lava.<REALM>.state`. It is used
to allow lava jobs to save state information for limited periods of time that
can be accessed by authorised external actors or other lava jobs.

Creation and reading of entries in the state table are managed by the lava
[state manager](#the-lava-state-manager). Other tools should not be used for this
purpose.

|Field|Type|Required|Description|
|-|-|-|-------------------------------------------------------------|
|state_id|String|Yes|The unique identifier for the state item.|
|publisher|String|No|An arbitrary identifier for the entity posting the event item. Not used by lava itself.|
|timestamp|String|No|An ISO 8601 format timestamp for the state item creation. Not used by lava itself.|
|ttl|Number|Yes|The epoch timestamp when the state record will expire. DynamoDB manages expiry automatically provided the TTL attribute for the table is set to `ttl`. The default and maximum time-to-live for entries in the table can be controlled by [worker configuration parameters](#lava-worker-configuration).|
|type|String|Yes|The state value type. This tells the lava worker how to decode the value. See [State Item Types](#state-item-types).|
|value|\*|Yes|The state value. The structure depends on the state type.|

### State Item Types

Each state record has a specified `type` that tells the worker how to decode the
`value`.  Within lava itself, this is largely transparent as the worker handles
all the necessary encoding and decoding.

The following types are supported:

|Type|Description|
|-|-------------------------------------------------------------|
|json|The value is stored as a JSON encoded object. This is the default as it provides the most fidelity in the encoding / decoding process. Lava does this automatically within its own universe. External actors should use the [lava state API](#the-lava-state-api) or the [lava state utility](#lava-state-utility) rather than attempt to reproduce this process natively.|
|raw|The value is stored as a DynamoDB object. This can sometimes do unhelpful type conversions on numbers.|
|secure|This uses the same value encoding mechanism as `json` with the addition of KMS encryption. Once again, external actors should use the [lava state API](#the-lava-state-api) or the [lava state utility](#lava-state-utility) rather than attempt to reproduce this process natively. KMS encryption imposes a maximum size limit of 4096 bytes on the JSON encoded state item value.|
