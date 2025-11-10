
## Job type: sharepoint_put_list

The **sharepoint_put_list** job type updates a SharePoint list from
a specified CSV source file.

Connection to the target SharePoint site is handled automatically by lava.

### Payload

The payload is ignored.

### Parameters

|Parameter|Type|Required|Description|
|-|-|-|-------------------------------------------------------------|
|basedir|String|No|If the source file is specified as a relative filename, it will be treated as relative to the specified directory. Defaults to the lava temporary directory for the job.|
|conn\_id|String|Yes|The [connection ID](#connector-type-sharepoint) for a SharePoint site.|
|data\_columns|String|No|A comma separated list of column names. If specified, then only columns listed are modified. Any columns specified in SharePoint as required must be included in the source data for modes `append` and `replace`. Required columns present in the source data will be included in the append/replace even if not explicitly included in the `data_columns` list.|
|delimiter|String|No|Single character field delimiter. Default `|`.|
|doublequote|Boolean|No|As for [csv.reader](https://docs.python.org/library/csv.html#csv-fmt-params). Default `false`.|
|error\_missing|Boolean|No|If `true` and there are columns in the source file that are not in the SharePoint list, raise an error. If `false`, the extra columns are silently ignored. Default `false`.|
|escapechar|String|No|As for [csv.reader](https://docs.python.org/library/csv.html#csv-fmt-params). Default `null`.|
|file|String|Yes|The source file name. If it starts with `s3://` it is assumed to be an object in S3, otherwise a local file. If a local file and not absolute, it will be relative to the `basedir` parameter. This value is Jinja rendered. The contents must be a CSV data with a single header line. The columns must match the pre-existing list in SharePoint.|
|jinja|Boolean|No|If `false`, disable Jinja rendering. Default `true`.|
|list|String|Yes|Name of the list. It must already exist in SharePoint. This will be jinja rendered.
|mode|String|No|See below. Default is `append`.|
|quotechar|String|No|As for [csv.reader](https://docs.python.org/library/csv.html#csv-fmt-params). Default `"`.|
|quoting|String|No|As for [csv.reader](https://docs.python.org/library/csv.html#csv-fmt-params) `QUOTE_*` parameters (without the QUOTE\_ prefix). Default `minimal` (i.e. `QUOTE_MINIMAL`).|
|vars|Map[String,\*]|No|A map of variables injected when the parameters are Jinja rendered.|


The `mode` parameter can take the following values:

|Mode|Description|
|-|-------------------------------------------------------------|
|append|Rows are added to the existing list contents.|
|delete|Rows are deleted based on an `ID` column that must be present in the source data. No new data is added.|
|replace|Existing list contents are a deleted before adding new data.|
|update|Rows are updated based on an `ID` column that must be present in the source data. Fields in existing rows may be updated but no new rows will be added.|

Note that any read-only columns in the SharePoint list are not updated.
These are silently skipped in the update process.

### Handling of personorgroup Columns { data-toc-label="Person-Or-Group Columns" }

Columns of type `personorgroup` have an associated `LookupId` column. So for a
column named `<COLUMN>`, the list also has a `<COLUMN>LookupId` column.

A `personorgroup` type column can only be updated if it’s provided using the
name `<COLUMN>LookupId` and the actual `LookupId` value

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

The **sharepoint_put_list** job behaviour is unchanged for dev mode.

### Examples

The following example replaces the contents of a list with data from S3.

```json
{
  "description": "Upload a CSV file to a SharePoint list",
  "dispatcher": "Sydney",
  "enabled": true,
  "job_id": "demo/sharepoint-list",
  "owner": "demo@somewhere.com",
  "parameters": {
    "conn_id": "sp-conn-01",
    "list": "My List",
    "file": "s3://my-bucket/x.csv",
    "mode": "replace"
  },
  "payload": "--",
  "type": "sharepoint_put_list",
  "worker": "default"
}
```
