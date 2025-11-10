
## Job type: smb_get

The **smb_get** job type downloads a file from an SMB file server to the
specified destination file.

Connection to the target SMB server is handled automatically by lava.

### Payload

The payload is ignored.

### Parameters

|Parameter|Type|Required|Description|
|-|-|-|-------------------------------------------------------------|
|basedir|String|No|If the target file is specified as a relative filename, it will be treated as relative to the specified directory. Defaults to the lava temporary directory for the job.|
|conn_id|String|Yes|The [connection ID](#connector-type-smb) for an SMB file share.|
|file|String|Yes|The destination file name. If it starts with `s3://` it is assumed to be an object in S3, otherwise a local file. If a local file and not absolute, it will be relative to the `basedir` parameter. This value is Jinja rendered.|
|jinja|Boolean|No|If `false`, disable Jinja rendering. Default `true`.|
|kms_key_id|String|No|An AWS KMS encryption key to use when uploading to AWS S3.|
|path|String|Yes|The source file path on the SMB file share. Use POSIX, not DOS, style path names (i.e. forward slash path separators). This value is Jinja rendered.|
|share_name|String|Yes|The name of the file share.|
|vars|Map[String,\*]|No|A map of variables injected when the parameters are Jinja rendered.|

### Jinja Rendering of Parameters

Some of the parameters are  rendered using [Jinja](http://jinja.pocoo.org).

All of the injected parameters are effectively Python objects so the normal
Jinja syntax and Python methods for those objects can be used in the Jinja
templates. This is particularly useful for the
[datetime](https://docs.python.org/3/library/datetime.html#datetime-objects)
objects as `strftime()` becomes available. For example, the source path can be
dynamically set to include components such as the date or part of the target
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

The following example downloads a file from an SMB file share and places it in
S3.  The file will be KMS encrypted in S3 with the specified KMS key.

```json
{
  "description": "Download a CSV file from a file share",
  "dispatcher": "Sydney",
  "enabled": true,
  "job_id": "demo/smb-get",
  "owner": "demo@somewhere.com",
  "parameters": {
    "conn_id": "smb-conn-01",
    "share_name": "Public",
    "path": "/Interesting/Data/x.csv",
    "file": "s3://my-bucket/x.csv",
    "kms_key_id": "alias/data"
  },
  "payload": "--",
  "type": "smb_get",
  "worker": "default"
}
```

This one shows how Jinja can be used to include the current date in the source
file name.


```json
{
  "description": "Download a CSV file from a file share",
  "dispatcher": "Sydney",
  "enabled": true,
  "job_id": "demo/smb-get",
  "owner": "demo@somewhere.com",
  "parameters": {
    "conn_id": "smb-conn-01",
    "share_name": "Public",
    "path": "/Interesting/Data/{{start.strftime('%Y-%m-%d')}}.csv",
    "file": "s3://my-bucket/{{start.strftime('%Y-%m-%d')}}.csv",
    "kms_key_id": "alias/data"
  },
  "payload": "--",
  "type": "smb_get",
  "worker": "default"
}
```
