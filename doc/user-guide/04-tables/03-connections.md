
## The Connections Table { data-toc-label="Connections" }

The connections table for a given `<REALM>` is named `lava.<REALM>.connections`.
It contains information to assist job handlers make connections to external
resources, typically databases.

|Field|Type|Required|Description|
|-|-|-|-------------------------------------------------------------|
|conn_id|String|Yes|Connection identifier.|
|description|String|No|A short description of the connection.|
|enabled|Boolean|Yes|Whether or not the connection is enabled. Defaults to `false`|
|owner|String|Not yet|Name or email address of the connection owner. **This field will be mandatory in a future release.**|
|type|String|Yes|The connection type. This is used to identify a [connector plugin](#connectors) to establish the connection.|
|X-\*|String|No|Any fields beginning with `x-` or `X-` are ignored by lava. These can be used as required for other purposes (e.g. CI/CD, versioning or other related purposes).|
|\*|\*|\*|All other fields are connection type specific. For more information see the section on [connectors](#connectors).|

