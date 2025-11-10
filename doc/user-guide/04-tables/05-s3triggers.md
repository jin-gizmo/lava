
## The S3triggers Table { data-toc-label="S3triggers" }

The s3triggers table for a given `<REALM>` is named `lava.<REALM>.s3triggers`.
It is used to map S3 bucket events to jobs. When an S3 event occurs with a
bucket and object prefix matching an entry in the table, the corresponding lava
job is dispatched. See
[Triggering Jobs from S3 Events](#dispatching-jobs-from-s3-events)
for more information.

|Field|Type|Required|Description|
|-|-|-|-------------------------------------------------------------|
|bucket|String|Yes|Bucket name.|
|delay|String|No|Dispatch message sending delay in the form `nnX` where `nn` is a number and `X` is `s` (seconds) or `m` (minutes). The maximum allowed value is 15 minutes.|
|description|String|No|A short description of the trigger.|
|enabled|Boolean|Yes|Whether or not the s3trigger is enabled.|
|globals|Map[String,\*]|No|A map of named values that are included in the dispatch request. These are Jinja rendered. Names beginning with `lava` (case insensitive) are reserved for lava's use. [More information on parameters and globals](#handling-of-parameters-and-globals-during-dispatch).|
|jinja|Boolean|No|If `false`, disable Jinja rendering of the parameters and globals. Defaults to `true`.|
|job_id|String \| List[String]|Yes|Job identifier for the lava job that will be dispatched, or a list of job identifiers. Each is Jinja rendered before use.|
|owner|String|Not yet|Name or email address of the trigger owner. **This field will be mandatory in a future release.**|
|parameters|Map[String,\*]|No|A map of parameters for the job that will be included in the dispatch. These will be Jinja rendered.|
|prefix|String|Yes|Object prefix. Do not include a trailing `/` or matches will fail. To indicate the root of the bucket, use a prefix value of `*`.|
|trigger_id|String|Yes|A unique identifier within the realm for the trigger entry.|
|X-\*|String|No|Any fields beginning with `x-` or `X-` are ignored by lava. These can be used as required for other purposes (e.g. CI/CD, versioning or other related purposes).|

In addition to the fields described above, entries in the S3 triggers tab may
also contain fields starting with `if_` and `if_not_`. These cause a test
to be applied to the S3 object event, The dispatch is only performed if the test
passes in the case of `if_` fields, or fails in the case of `if_not_` fields.
The available `if_` tests are described below. There is a corresponding
`if_not_` test for each.

|Field|Type|Required|Description|
|-|-|-|-------------------------------------------------------------|
|if_fnmatch|String \| List[String]|No|Perform a glob style match against the S3 object key. If a list of patterns is provided, returns true if any of the patterns match the key. The matching rules defined by Python's [fnmatch](https://docs.python.org/3/library/fnmatch.html#fnmatch.fnmatch) apply.|
|if_size_gt|Integer \| String|No|Check that the S3 object is larger than the specified size. Values can be specified as an integer or a string in the form `nnX`, where `n` is a number and `X` is an optional unit such as 'K', 'KB', 'KiB', 'MiB' etc. Default for `X` is bytes.||
|if_event_type|String|No|Check that the S3 event type matches the specified value (e.g. `ObjectCreated:Put`). Glob style patterns are accepted (e.g. `ObjectCreated:*`).|
