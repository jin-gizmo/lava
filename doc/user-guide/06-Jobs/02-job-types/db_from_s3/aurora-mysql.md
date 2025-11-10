
### Loading Data to Aurora MySQL

Loading to Amazon Aurora MySQL is done using the native
[LOAD DATA FROM S3](https://docs.aws.amazon.com/AmazonRDS/latest/AuroraUserGuide/AuroraMySQL.Integrating.LoadFromS3.html#AuroraMySQL.Integrating.LoadFromS3.Text)
facility.

There are a number of preliminary setup steps required on the database itself to
enable this mechanism. Once enabled, it can load uncompressed data. Loading of
compressed data is not supported.

#### Aurora MySQL Specific Parameters

The `db_conn_id` parameter must point to a connection with a `type` of
[mysql-aurora](#connector-type-mysql-aurora).

The loading operation relies on pre-configuration on the cluster itself to
provide access to S3. The `s3_conn_id` and `s3_iam_role` parameters are not
used.

!!! note
    The syntax of the [LOAD DATA FROM
    S3](https://docs.aws.amazon.com/AmazonRDS/latest/AuroraUserGuide/AuroraMySQL.Integrating.LoadFromS3.html#AuroraMySQL.Integrating.LoadFromS3.Text)
    command is very different from its Postgres and Redshift counterparts. Lava
    attempts to reduce the apparent differences by adopting some of the Redshift
    / Postgres conventions in the `args` parameter. Whether this is helpful or
    dangerous folly is in the eye of the beholder.

The `args` parameter must contain a list of 
[Aurora MySQL LOAD DATA](https://docs.aws.amazon.com/AmazonRDS/latest/AuroraUserGuide/AuroraMySQL.Integrating.LoadFromS3.html#AuroraMySQL.Integrating.LoadFromS3.Text) command options. See also
the [standard MySQL LOAD DATA reference](https://dev.mysql.com/doc/refman/5.6/en/load-data.html).
Only the following options are supported:

*   FILE
*   IGNORE
*   MANIFEST
*   PARTITION
*   PREFIX
*   REPLACE

In addition, the following non-standard options are supported:

|Option|Description|
|-|-------------------------------------------------------------|
|DELIMITER|Takes an argument of the form `'string'` specifying the column delimiter.|
|ENCODING|Takes an argument specifying the character set of the data.|
|ESCAPE|Takes an argument of the form `'char'` specifying the character used to escape quote characters.|
|HEADER|Takes an optional integer argument specifying the number of header lines to skip. The default value is `1`.|
|QUOTE|Takes arguments of the form `[OPTIONAL] 'char'` specifying the character used to quote data fields. If the `OPTIONAL` keyword is present, only fields with a string type are quoted. If omitted, all fields are quoted.|
|TERMINATOR|Takes an argument in the form `DOS | UNIX | 'char'`. The `DOS` and `UNIX` options set the line terminator appropriate for data sourced from those systems.|


#### Aurora MySQL Examples

The following example shows loading of a data file to a table in `switch` mode.
The tables `membership_a` and `membership_b` will be created with the given
column specifications if they don't already exist.

```json
{
  "description": "Copy data to the table 'custardclub.membership'",
  "dispatcher": "Sydney",
  "enabled": true,
  "job_id": "demo/copy-mytable",
  "owner": "demo@somewhere.com",
  "parameters": {
    "db_conn_id": "mysql-aurora-conn-01",
    "bucket": "my-bucket",
    "key": "a/b/data.csv",
    "schema": "custardclub",
    "table": "membership",
    "mode": "switch",
    "args": [
      "DELIMITER ','",
      "HEADER",
      "ENCODING utf8",
      "QUOTE OPTIONAL '\"'",
      "TERMINATOR UNIX"
    ],
    "columns": [
      "CustardClubNo INTEGER PRIMARY KEY NOT NULL",
      "GivenName VARCHAR(20)",
      "FamilyName VARCHAR(30)",
      "CustardBidPrice FLOAT(2)",
      "CustardJedi BOOLEAN",
      "LastCustard DATE",
      "CustardQuota INTEGER"
    ]
  },
  "payload": "--",
  "type": "db_from_s3",
  "worker": "default"
}
```

