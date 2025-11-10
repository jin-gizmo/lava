
## Job type: sharepoint_get_list

The **sharepoint_get_list** job type downloads a SharePoint list to a
a specified destination file, one row per line.

Connection to the target SharePoint site is handled automatically by lava.

### Payload

The payload is ignored.

### Parameters

The formatting related parameters are as defined for the Python CSV writer,
although some of the defaults are different.  Defaults can be overridden at the
realm level using [configuration
variables](#configuration-for-sharepoint-jobs).

|Parameter|Type|Required|Description|
|-|-|-|-------------------------------------------------------------|
|basedir|String|No|If the target file is specified as a relative filename, it will be treated as relative to the specified directory. Defaults to the lava temporary directory for the job.|
|conn\_id|String|Yes|The [connection ID](#connector-type-sharepoint) for a SharePoint site.|
|data\_columns|String|No|A comma separated list of column names. If specified, then only columns listed are extracted (in addition to any specified `system_columns`).|
|delimiter|String|No|Single character field delimiter. Default `|`.|
|doublequote|Boolean|No|As for [csv.writer](https://docs.python.org/library/csv.html#csv-fmt-params). Default `false`.|
|escapechar|String|No|As for [csv.writer](https://docs.python.org/library/csv.html#csv-fmt-params). Default `null`.|
|file|String|Yes|The destination file name. If it starts with `s3://` it is assumed to be an object in S3, otherwise a local file. If a local file and not absolute, it will be relative to the `basedir` parameter. This value is Jinja rendered.|
|header|Boolean|No|If `true`, include a header line containing column names. Default `true`.|
|jinja|Boolean|No|If `false`, disable Jinja rendering. Default `true`.|
|kms\_key\_id|String|No|An AWS KMS encryption key to use when uploading to AWS S3.|
|list|String|Yes|Name of the list. It must already exist in SharePoint. This will be jinja rendered.
|quotechar|String|No|As for [csv.writer](https://docs.python.org/library/csv.html#csv-fmt-params). Default `"`.|
|quoting|String|No|As for [csv.writer](https://docs.python.org/library/csv.html#csv-fmt-params) `QUOTE_*` parameters (without the QUOTE\_ prefix). Default `minimal` (i.e. `QUOTE_MINIMAL`).|
|system\_columns|String|No|A comma separated list of system columns to retrieve in addition to the data columns. Unless specified, only data columns are retrieved.|
|vars|Map[String,\*]|No|A map of variables injected when the parameters are Jinja rendered.|

Consult SharePoint documentation for available system columns. Currently known
columns include:

*   `ComplianceAssetId`
*   `AppAuthor`
*   `AppEditor`
*   `Attachments`
*   `Author`
*   `ContentType`
*   `Created`
*   `DocIcon`
*   `Edit`
*   `Editor`
*   `FolderChildCount`
*   `ID`
*   `ItemChildCount`
*   `LinkTitleNoMenu`
*   `LinkTitle`
*   `Modified`
*   `_ComplianceFlags`
*   `_ComplianceTagUserId`
*   `_ComplianceTagWrittenTime`
*   `_ComplianceTag`
*   `_IsRecord`
*   `_UIVersionString`

### Handling of personorgroup Columns { data-toc-label="Person-Or-Group Columns" }

Columns of type `personorgroup` have an associated `LookupId` column. So for a
column named `<COLUMN>`, the list also has a `<COLUMN>LookupId` column.

If the `data_columns` parameter is not specified, meaning to retrieve all
columns, the `<COLUMN>` and `<COLUMN>LookupId` will both be retrieved, in that
order.

If the `data_columns` parameter is specified, the `<COLUMN>LookupId` must be
explicitly named in the list if required.

System columns of type `personorgroup` also have an associated `LookupId` column
that can be retrieved by naming it in the `system_columns` parameter.

### Jinja Rendering of Parameters

Some of the parameters are  rendered using [Jinja](http://jinja.pocoo.org).

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

The **sharepoint_get_list** job behaviour is unchanged for dev mode.

### Examples

The following example replaces the contents of a list with data from S3.


```json
{
  "description": "Download a SharePoint list to a CSV file",
  "dispatcher": "Sydney",
  "enabled": true,
  "job_id": "demo/sharepoint-list",
  "owner": "demo@somewhere.com",
  "parameters": {
    "conn_id": "sp-conn-01",
    "list": "My List",
    "file": "s3://my-bucket/x.csv",
    "kms_key_id": "alias/data",
    "quote": "minimal",
    "separator": ","
  },
  "payload": "--",
  "type": "sharepoint_get_list",
  "worker": "default"
}
```
