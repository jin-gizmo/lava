
## Job type: foreach

The **foreach** job type runs a single specified job in a loop.

Like the [chain](#job-type-chain) job type, this is a synchronous operation. The
parent **foreach** job and the child job must be set to run on the same worker
and the parent and all child iterations will run under the `run_id` of the
parent job.

Any globals available in the **foreach** job will also be passed to each
iteration of the child job, with additional, iteration specific, globals
injected for each iteration.  A loop index counter
(`globals.lava.foreach_index`) is also made available to child iterations in the
[globals owned by lava](#globals-owned-by-lava).


### Payload

The `payload` is the `job_id` of the job to be iterated.

### Parameters

|Parameter|Type|Required|Description|
|-|---------|-|-------------------------------------------------------------|
| can\_fail | Boolean | No |A boolean that indicates if individual iterations are permitted to fail without causing the entire job to fail. Defaults to `false`. See [Allowing Foreach Child Jobs to Fail](#allowing-foreach-child-jobs-to-fail).|
| foreach | Map[String,*] | Yes |This parameter specifies the mechanism used to generate named values for each iteration. It is effectively a Python-like iterator yielding a dictionary of values for each iteration that is merged into the globals for the child job. See [Foreach Value Generators](#foreach-value-generators).|
| limit | Integer | No | An integer. Attempting to run a **foreach** job with more than this many loop iterations will fail without any job being run at all. Defaults to the realm level value as specified by the [FOREACH_LIMIT](#configuration-for-foreach-jobs) configuration parameter.|
| jinja | Boolean | No | If true (the default), enable Jinja rendering. What gets rendered in the `foreach` generator specification is controlled by the generator itself. |

### Foreach Value Generators

The `foreach` parameter is a map that defines the mechanism used to generate a
set of named values for each loop iteration. These named values are merged into
the globals passed to the child job.

Value generation is as lazy as possible to minimise overheads and memory usage.

!!! info
    It is not permitted for any value names returned by a `foreach` generator to
    begin with `lava` (case independent).

Apart from the common `type` field, the other fields in the `foreach` parameter
depend on the `type`. Field values are *not* Jinja rendered unless indicated
otherwise below.


#### Foreach type: CSV

The **csv** generator reads data from a CSV file. The file must have a header to
provide the names of values generated for each `foreach` iteration.

| Field | Type | Required | Description |
|-|-|-|------------------|
| type | String | Yes | The foreach generator type: `csv`. |
| filename | String | Yes | The name of the CSV file, which can be local or in S3 (`s3://...`). This field is Jinja rendered. |

For example, given this CSV source file ...

```csv
a,b
a0,b0
a1,b1
```

... the globals of the child job would have `globals.a=a0` on the first
iteration and `globals.a=a1` on the second.

#### Foreach type: inline

The **inline** generator contains the iteration values within the `foreach`
parameter itself.

| Field | Type | Required | Description |
|-|-|-|------------------|
| type | String | Yes | The foreach generator type: `inline`. |
| values | List[Map[String,*]] | Yes | A list of maps containing iteration values. |

For example, given this (partial) job specification ...

```json
{
  "job_id": "example",
  "type": "foreach",
  "payload": "child_job_id",
  "parameters": {
    "foreach": {
      "type": "inline",
      "values": [
        {"a": "a0", "b": "b0" },
        {"a": "a1", "b": "b1" }
      ]
    }
  }
}
```

... the globals of the child job would have `globals.a=a0` on the first
iteration and `globals.a=a1` on the second.

!!! note
    It is not required that each value map in the list has the same keys,
    although it would be an unusual use-case.

#### Foreach type: jsonl

The **jsonl** generator reads JSON encoded objects from a file, one object per
line.

| Field | Type | Required | Description |
|-|-|-|------------------|
| type | String | Yes | The foreach generator type: `jsonl`. |
| filename | String | Yes | The name of the JSONL file, which can be local or in S3 (`s3://...`). This field is Jinja rendered. |

For example, given this JSONL source file ...

```json
{"a": "a0", "b": "b0" }
{"a": "a1", "b": "b1" }
```

... the globals of the child job would have `globals.a=a0` on the first
iteration and `globals.a=a1` on the second.

!!! note
    It is not required that each JSON line has the same keys, although it would
    be an unusual use-case.

#### Foreach type: query

The **query** generator obtains iteration values from a database query. 


| Field | Type | Required | Description |
|-|-|-|------------------|
| type | String | Yes | The foreach generator type: `query`. |
| conn\_id | String | Yes | The [connection ID](#database-connectors) for a target database. |
| query | String | Yes | The query to provide iteration values. Each row provides one set of iteration values. The field names are derived from the column names in the query. Take care to specify useful column names in the query when using database functions. |

!!! question "But but but ..."
    No, the query text is not Jinja rendered ... and it won't be.

For example, given this (partial) job specification ...

```json
{
  "job_id": "example",
  "type": "foreach",
  "payload": "child_job_id",
  "parameters": {
    "foreach": {
      "type": "query",
      "conn_id": "my_db_conn_id",
      "query": "SELECT a, COUNT(*) AS b FROM some.table GROUP by 1 LIMIT 5"
    }
  }
}
```

... would generate up to 5 iterations, each containing an `a` and `b` global.

!!! note
    Be careful about producing too many rows or including unnecessary values.
    The `limit` parameter will force the job to abort if more than that many
    rows are produced. Use database views to effect here.


#### Foreach type: range

The **range** generator behaves in the same way as the Python
[range()](https://docs.python.org/3/library/functions.html#func-range)
mechanism.

| Field | Type | Required | Description |
|-|-|-|------------------|
| type | String | Yes | The foreach generator type: `range`. |
| name | String | No | If specified, the current value of the range counter is made available in a global with this name. This value may be different from `lava.globals.foreach_index` which always counts up from `0`. |
| start | Integer | No | The starting index for the range. Default is `0`. |
| stop | Integer | Yes | The value of the `stop` parameter. |
| step | Integer | No | The value of the `step` parameter. Default is `1`. |

For example, given this (partial) job specification ...

```json
{
  "job_id": "example",
  "type": "foreach",
  "payload": "child_job_id",
  "parameters": {
    "foreach": {
      "type": "range",
      "name": "a",
      "stop": 2
    }
  }
}
```

... the globals of the child job would have `globals.a=0` on the first
iteration and `globals.a=1` on the second.

#### Foreach type: s3list

The **s3list** generator produces a list of objects in an AWS S3 bucket.

| Field | Type | Required | Description |
|-|-|-|------------------|
| type | String | Yes | The foreach generator type: `s3list`. |
| bucket | String | Yes | The S3 bucket name. This field is Jinja rendered. |
| prefix | String | No | The S3 prefix to list. Defaults to the bucket root. This field is Jinja rendered. |
| glob | String\|List[String] | No | A glob style pattern, or list of patterns. Only S3 objects with names matching any of the patterns are returned. |

A (partial) job specification might look like so:

```json
{
  "job_id": "example",
  "type": "foreach",
  "payload": "child_job_id",
  "parameters": {
    "foreach": {
      "type": "s3list",
      "bucket": "my-bucket",
      "prefix": "a/prefix/",
      "glob": [
        "*.csv",
        "*.jsonl"
      ]
    }
  }
}
```

Each element returned by the generator to be added to the child globals is of
the form:

```python
{
    's3obj': {
        'Bucket': 'my-bucket',
        'Key': 'a/prefix/somewhere/in/s3.jsonl',
        'LastModified': datetime.datetime(2024, 1, 1, 6, 2, 59, tzinfo=tzutc()),
        'ETag': '"be0c0123456789abcd0123456678916a"',
        'Size': 197,
        'StorageClass': 'STANDARD'
    }
}
```

The value in the dictionary shown above is the object returned in the `Contents`
list in the response to the boto3 S3 client
[list_objects_v2](https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/s3/client/list_objects_v2.html)
function, with the addition of the bucket name.

In the example shown above, the child job could access the full S3 object name
as:

```jinja
s3://{{ globals.s3obj.Bucket }}/{{ globals.s3obj.Key }}
```

### Allowing Foreach Child Jobs to Fail { data-toc-label="Allowing Child Jobs to Fail" }

By default, the **foreach** loop is aborted when any iteration fails unless
the `can_fail` parameter is set to `true`. In this case, the iteration process
will continue and the master **foreach** job will succeed even if child
iterations fail. In this situation, it is important that
the child job handles its own [on\_fail](#job-actions) actions, as the parent
will not. Suck it up kid.

This tolerance of failure does not include configuration errors in the child
job, such as a malformed job specification, child job sent to the wrong worker
etc. This will still cause the entire **foreach** job to fail.

!!! note "Keep Calm"
    Before anyone gets all bitter and twisted about *can* vs *may* in
    `can_fail`...  both are essentially equivalent in this crazy, modern world.
    Look it up.

### Handling of Globals

The **foreach** job type merges its globals into those of the child job for
each iteration. A value specified in the parent **foreach** job will override a
similarly named value in the child.

The globals generated by the [foreach](#foreach-value-generators) iteration
generator will override any existing global with the same name.

The **foreach** job will also add [lava specific globals](#globals-owned-by-lava)
under `globals.lava`. These lava owned globals allow all child iterations, to
access some common global values. An attempt by the
[foreach](#foreach-value-generators) iteration generator to override any of
these will cause the job to fail.

The `global.lava.foreach_index` global is special. It is a counter, starting at
zero for the first loop iteration, and incremented by one for each iteration.

### Dev Mode Behaviour

The **foreach** job behaviour is unchanged for dev mode. However, dev mode is
propagated to child jobs.
