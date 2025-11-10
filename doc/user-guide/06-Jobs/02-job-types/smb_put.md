
## Job type: smb_put

The **smb_put** job type creates or updates a file on an SMB file share from a
specified source file.

Connection to the target SMB server is handled automatically by lava.

### Payload

The payload is ignored.

### Parameters

|Parameter|Type|Required|Description|
|-|-|-|-------------------------------------------------------------|
|basedir|String|No|If the source file is specified as a relative filename, it will be treated as relative to the specified directory. Defaults to the lava temporary directory for the job.|
|conn_id|String|Yes|The [connection ID](#connector-type-smb) for an SMB server.|
|create_dirs|Boolean|No|If `true`, the target directory, including parent directories, will be created if it doesn't exist. Default is `false`.|
|file|String|Yes|The source file name. If it starts with `s3://` it is assumed to be an object in S3, otherwise a local file. If a local file and not absolute, it will be relative to the `basedir` parameter. This value is Jinja rendered.|
|jinja|Boolean|No|If `false`, disable Jinja rendering. Default `true`.|
|path|String|Yes|The target path on the SMB file share. Use POSIX, not DOS, style path names (i.e. forward slash path separators). This value is Jinja rendered.|
|share_name|String|Yes|The name of the file share.|
|vars|Map[String,\*]|No|A map of variables injected when the parameters are Jinja rendered.|

### Jinja Rendering of Parameters

Some of the parameters are rendered using [Jinja](http://jinja.pocoo.org).

All of the injected parameters are effectively Python objects so the normal
Jinja syntax and Python methods for those objects can be used in the Jinja
templates. This is particularly useful for the
[datetime](https://docs.python.org/3/library/datetime.html#datetime-objects)
objects as `strftime()` becomes available. For example, target path can be
dynamically set to include components such as the date or part of the source
file name.

Refer to [Jinja Rendering in Lava](#jinja-rendering-in-lava)
for more information.

The following variables are made available to the renderer.

|Name|Type|Description|
|-|-|-------------------------------------------------------------|
|globals|dict[str,\*]|The `globals` from the job specification updated with any globals received in the job dispatch.|
|job|dict[str,\*]|The [augmented job specification](#the-augmented-job-specification).|
|realm|dict[str,\*]|The realm specification.|
|start|datetime|The local time when the job run started.|
|state|dict[str,\*]|A dictionary of the state items imported into the job, keyed on state_id. The default values are updated at run-time with any current values obtainable from the [state](#the-state-table) table.|
|ustart|datetime|The UTC time when the job run started.|
|utils|dict[str,runnable]|A dictionary of [utility functions](#jinja-utility-functions) that can be used in the Jinja markup.|
|vars|dict[str,\*]|A dictionary of variables provided as the `vars` component of the job `parameters`.|

### Dev Mode Behaviour

Job behaviour is unchanged for dev mode.

### Examples

The following example uploads a file from S3 to an SMB file share.

```json
{
  "description": "Upload a CSV file to an SMB file share",
  "dispatcher": "Sydney",
  "enabled": true,
  "job_id": "demo/smb-put",
  "owner": "demo@somewhere.com",
  "parameters": {
    "conn_id": "smb-conn-01",
    "share_name": "Public",
    "path": "/Interesting/Data/x.csv",
    "file": "s3://my-bucket/x.csv"
  },
  "payload": "--",
  "type": "smb_put",
  "worker": "default"
}
```

This one shows how Jinja can be used to replicate the source file name into
the target file name.


```json
{
  "description": "Upload a CSV file to an SMB file share",
  "dispatcher": "Sydney",
  "enabled": true,
  "job_id": "demo/smb-put",
  "owner": "demo@somewhere.com",
  "parameters": {
    "conn_id": "smb-conn-01",
    "share_name": "Public",
    "path": "/Interesting/Data/{{job.parameters.file}}.split('/')[-1]}}",
    "file": "s3://my-bucket/x.csv"
  },
  "payload": "--",
  "type": "smb_put",
  "worker": "default"
}
```

This one shows how Jinja can be used to include the current date in the target
path. Note that target directories are created on the fly.


```json
{
  "description": "Upload a CSV file to an SMB file share",
  "dispatcher": "Sydney",
  "enabled": true,
  "job_id": "demo/smb-put",
  "owner": "demo@somewhere.com",
  "parameters": {
    "conn_id": "sp-conn-01",
    "share_name": "Public",
    "path": "/Interesting/Data/{{start.strftime('%Y/%m/%d')}}/data.csv",
    "file": "s3://my-bucket/x.csv",
    "title": "This is an interesting data set",
    "create_dirs": true
  },
  "payload": "--",
  "type": "smb_put",
  "worker": "default"
}
```
