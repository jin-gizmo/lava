
## Job type: redshift_unload

The **redshift_unload** job type performs an
[UNLOAD](https://docs.aws.amazon.com/redshift/latest/dg/r_UNLOAD.html) operation
on an AWS Redshift cluster.

### Payload

The payload is ignored.

### Parameters

|Parameter|Type|Required|Description|
|-|-|-|-------------------------------------------------------------|
|args|List[String]|Yes|A list of options for the `UNLOAD` command. All of the Redshift supported parameters except for the authorisation parameters are supported. The options are pre-processed before passing to Redshift as described [below](#handling-of-redshift-unload-options).|
|bucket|String|Yes|The name of the S3 bucket to which the data is unloaded.|
|conn\_id|String|Yes|The connection ID for a [Redshift provisioned cluster](#connector-type-redshift) or a [Redshift Serverless workgroup](#connector-type-redshift-serverless).|
|dateformat|String|No|A Redshift [datetime format string](https://docs.aws.amazon.com/redshift/latest/dg/r_FORMAT_strings.html) that will be applied to DATE fields when unloading. The safest value is `YYYY-MM-DD`. [More information on date formats](#date-formatting).|
|insecure|Boolean|No|Disable [bucket security checks](#s3-bucket-security-checks). Default is false.|
|prefix|String|Yes|The prefix in the S3 bucket to which the data is unloaded. This value is [Jinja rendered](#jinja-rendering-of-the-s3-target-key) prior to use.|
|relation|String _or_ List[String]|Yes|The name of the table or view to be unloaded (without schema) or a list of names.|
|s3\_conn\_id|String|No|The [connection ID](#connector-type-aws) for AWS S3. This is used in the `UNLOAD` command to allow Redshift access to S3. Either `s3_conn_id` or `s3_iam_role` is required.|
|s3\_iam\_role|String|No|The IAM role name to use in the `UNLOAD` command to allow Redshift access to S3. Either `s3_conn_id` or `s3_iam_role` is required.|
|schema|String|Yes|The name of the source schema for the object to be unloaded.|
|start|String|No|Name of the relation to start with when unloading a list of relations. If not specified, start at the beginning of the list. This is useful when `stop_on_fail` is false and an unload fails as it allows the unloads to be resumed at the point of failure once the issue is rectified.|
|stop\_on\_fail|Boolean|No|If true, stop when any unload fails otherwise keep moving through the unload list. Default is true. The event record for the job will indicate which unloads succeeded and which failed.|
|vars|Map[String,\*]|No|A map of variables injected when the S3 target prefix is Jinja rendered.|
|where|String|No|An optional `WHERE` condition for the `UNLOAD` queries. Do not include the `WHERE` keyword. Note that the same condition will be added to each unload if multiple relations are specified.|

### Handling of Redshift Unload Options { data-toc-label="Redshift Unload Options" }

The options for the Redshift
[UNLOAD](https://docs.aws.amazon.com/redshift/latest/dg/r_UNLOAD.html) command
specified in the `args` key of the job parameters are pre-processed prior to use
in the `UNLOAD` operation. Unless otherwise specified below, the option is
passed through unmodified.

#### Partition Option

The `PARTITION` option is supplied to the `UNLOAD` command in the following form:

```
PARTITION BY (col1, col2,...)
```

If the unload `args` contain the `PARTITION` clause in this format, it is used as is.

The unload `args` can instead contain a `PARTITION` clause in this format:

```
PARTITION BY @<SCHEMA_NAME>.<REL_NAME>
```

In this case, the partition information is assumed to be contained in a
partition table (or view) `<SCHEMA_NAME>.<REL_NAME>` that resides in the same
Redshift cluster as the source relation. The partition table (or view) must
include the following columns:

|Name|Type|Description|
|-|-|--------------------|
|schema_name|VARCHAR(127)|Schema name in lower case.|
|rel_name|VARCHAR(127)|Table or view name in lower case.|
|partitions|VARCHAR(n)|A comma separated list of columns in the relation that will be used to populate the partition column list in the `UNLOAD` command.|

The following SQL DDL would create a suitable partition table.

```sql
CREATE TABLE metadata.partitions
(
    schema_name VARCHAR(127)  NOT NULL,
    rel_name    VARCHAR(127)  NOT NULL,
    partitions  VARCHAR(2048) NOT NULL,
    PRIMARY KEY (schema_name, rel_name)
)
```

The `PARTITION` argument in the job parameters would then look like:

```
PARTITION BY @metadata.partitions
```

### Date Formatting

Redshift has some very nasty behaviour in its date handling. It will UNLOAD
date fields with years less than 100 in `YY-MM-DD` format. Madness.

Redshift COPY using `DATEFORMAT 'auto'` assumes dates in `YY-MM-DD` format must
be Y2K adjusted (i.e. they are moved to post 2000). More madness.

So, an UNLOAD followed by a COPY will mangle dates. While the COPY command
could specify `DATEFORMAT 'YY-MM-DD'`, this will then fail for any dates with
years greater than 99. So, if the column contains dates before and after the
year 100, you're in trouble.

In short, there is no reliable way to UNLOAD and then COPY a data set containing
dates without manually formatting date fields.

To get around this singular piece of genius, use the `dateformat` key in the job
parameters.

If the `dateformat` key is present, and the relation has one or more DATE
fields, **redshift_unload** will construct a SELECT statement for the unload
that includes all of the columns, applying the given date format to DATE
columns. This is likely to impact UNLOAD performance, so it's best to avoid
using it if you are certain all dates have years greater than 99. The safest
format value is probably `YYYY-MM-DD`.

If the `dateformat` key is not present, or the relation has no DATE columns,
**redshift_unload** will simply use `SELECT *` for the target relation in the
UNLOAD command.

### Jinja Rendering of the S3 Target Key { data-toc-label="Jinja Rendering of the S3 Key" }

The `prefix` parameter specifies the UNLOAD location in the target bucket. Its
value is rendered using [Jinja](http://jinja.pocoo.org) to allow injection of
parameters relevant to the individual job specification and run.

!!! info
    If a list of relations is to be unloaded, it is important to use this
    rendering facility to ensure that each relation is unloaded to its own area
    in S3.

All of the injected parameters are effectively Python objects so the normal
Jinja syntax and Python methods for those objects can be used in the Jinja
templates. This is particularly useful for the
[datetime](https://docs.python.org/3/library/datetime.html#datetime-objects)
objects as `strftime()` becomes available. For example, the S3 location of
the unload (`prefix`) can be dynamically set to include components such as the
schema, relation name, unload date etc.

Refer to [Jinja Rendering in Lava](#jinja-rendering-in-lava)
for more information.

The following variables are made available to the renderer.

|Name|Type|Description|
|-|-|-------------------------------------------------------------|
|globals|dict[str,\*]|The `globals` from the job specification updated with any globals received in the job dispatch.|
|job|dict[str,\*]|The [augmented job specification](#the-augmented-job-specification).|
|realm|dict[str,\*]|The realm specification.|
|relation|str|The relation name.|
|schema|str|The schema name.|
|start|datetime|The local time when the job run started.|
|state|dict[str,\*]|A dictionary of the state items imported into the job, keyed on state_id. The default values are updated at run-time with any current values obtainable from the [state](#the-state-table) table.|
|ustart|datetime|The UTC time when the job run started.|
|utils|dict[str,runnable]|A dictionary of [utility functions](#jinja-utility-functions) that can be used in the Jinja markup.|
|vars|dict[str,\*]|A dictionary of variables provided as the `vars` component of the job `parameters`.|

### S3 Bucket Security Checks

**Redshift_unload** performs some basic checks on the security of
the target S3 bucket to reduce the risk of unloading data to somewhere unsafe.
This is a convenience only and should not be relied upon for securing your data.

By default, if any of the following are true, the bucket will not be used
for unloaded data and the job run will fail:

*   The bucket has any form of public access

*   The bucket does not have default encryption enabled

*   Server logging is not enabled on the bucket

*   The bucket is owned by an AWS account other than the one associated with the
    profile being used by the lava worker.

These security checks can be disabled by setting the `insecure` parameter to
`true`.

If the security checks are enabled, the lava worker will require the following
additional IAM permissions on the target bucket:

*   List all buckets: `s3:ListAllMyBuckets`

*   Get bucket logging configuration: `s3:GetBucketLogging`

*   Get bucket encryption configuration: `s3:GetEncryptionConfiguration`

*   Get bucket ACLs: `s3:GetBucketAcl`

### Dev Mode Behaviour

The **redshift_unload** job behaviour is unchanged for dev mode.

### Examples

The following example will unload the table `mytable`

```json
{
  "description": "Unload the table 'mytable'",
  "dispatcher": "Sydney",
  "enabled": true,
  "job_id": "demo/unload-mytable",
  "owner": "demo@somewhere.com",
  "parameters": {
    "args": [
      "parallel on",
      "delimiter '|'",
      "kms_key_id 'alias/lava-proto-user'",
      "encrypted",
      "header",
      "allowoverwrite"
    ],
    "bucket": "my-bucket",
    "conn_id": "redshift-conn-01",
    "dateformat": "YYYY-MM-DD",
    "prefix": "unload_demo/{{schema}}/{{relation}}/",
    "relation": "mytable",
    "s3_conn_id": "s3-conn-01",
    "schema": "public"
  },
  "payload": "--",
  "type": "redshift_unload",
  "worker": "default"
}
```

This one unloads the same table but the destination in S3 includes a date
component.


```json
{
  "description": "Unload the table 'mytable'",
  "dispatcher": "Sydney",
  "enabled": true,
  "job_id": "demo/unload-mytable",
  "owner": "demo@somewhere.com",
  "parameters": {
    "args": [
      "parallel on",
      "delimiter '|'",
      "kms_key_id 'alias/lava-proto-user'",
      "encrypted",
      "header",
      "allowoverwrite"
    ],
    "bucket": "my-bucket",
    "conn_id": "redshift-conn-01",
    "dateformat": "YYYY-MM-DD",
    "prefix": "unload_demo/{{schema}}/{{relation}}/{{start.strftime('%Y/%m/%d')}}/",
    "relation": "mytable",
    "s3_conn_id": "s3-conn-01",
    "schema": "public"
  },
  "payload": "--",
  "type": "redshift_unload",
  "worker": "default"
}
```

This one unloads a list of tables.


```json
{
  "description": "Unload multiple tables",
  "dispatcher": "Sydney",
  "enabled": true,
  "job_id": "demo/unload-multi",
  "owner": "demo@somewhere.com",
  "parameters": {
    "args": [
      "parallel on",
      "delimiter '|'",
      "kms_key_id 'alias/lava-proto-user'",
      "encrypted",
      "header",
      "allowoverwrite"
    ],
    "bucket": "my-bucket",
    "conn_id": "redshift-conn-01",
    "dateformat": "YYYY-MM-DD",
    "prefix": "unload_demo/{{schema}}/{{relation}}/{{start.strftime('%Y/%m/%d')}}/",
    "relation": [
      "mytable",
      "yourtable"
    ],
    "s3_conn_id": "s3-conn-01",
    "schema": "public"
  },
  "payload": "--",
  "type": "redshift_unload",
  "worker": "default"
}
```
