
### Loading Data to Postgres RDS

Loading to Postgres RDS and Aurora Postgres is done using the native
[aws_s3.table_import_from_s3](https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/PostgreSQL.Procedural.Importing.html)
facility. This is supported in the following versions:

*   AWS RDS PostgreSQL versions 11.1+
*   AWS RDS Aurora PostgreSQL-compatible versions 10.7+

There are a number of
[preliminary setup steps](#enabling-the-postgres-rds-copy-extension)
required on the database itself to enable this mechanism. Once enabled, it can
load uncompressed data and gzip compressed data.

#### Postgres RDS Specific Parameters

The `db_conn_id` parameter must point to a connection with a `type` of either
[postgres-aurora](#connector-type-postgres-aurora) or
[postgres-rds](#connector-type-postgres-rds).

If the `s3_conn_id` parameter is specified, the relevant connector will be used
to provide credentials to access S3. If the parameter is not specified, the
database must have an attached IAM role that provides the required access to S3.
As this is implicit, there is no need to specify the `s3_conn_id` parameter.

The `args` parameter must contain a list of Postgres
[COPY](https://www.postgresql.org/docs/10/sql-copy.html) command options
appropriate for the data file.

The following options are supported:

*   DELIMITER
*   ENCODING
*   ESCAPE
*   FORCE\_NOT\_NULL (see below)
*   FORCE\_NULL (see below)
*   FORMAT
*   FREEZE
*   HEADER
*   NULL
*   OIDS
*   QUOTE

In addition, the following non-standard options are supported:

|Option|Description|
|-|-------------------------------------------------------------|
|FORCE\_NOT\_NULL|As for `FORCE_NULL`.|
|FORCE\_NULL|This standard option accepts a non-standard `*` argument which lava will replace with a list of all columns in the target table.|
|GZIP|The Postgres copy operation can load gzip compressed data but the S3 object being loaded must have its `Content-Encoding` metadata set to `gzip`. If this option is specified, lava will attempt to set the content encoding appropriately if necessary. Be aware that this is, in fact, an object copy operation with new metadata so the worker will require appropriate IAM permissions to do that.|
|MANIFEST|The S3 object will be treated as a [Redshift compatible manifest](https://docs.aws.amazon.com/redshift/latest/dg/loading-data-files-using-manifest.html) containing a list of actual data files to load.|

!!! info
    When configuring a bucket event notification for s3trigger to dispatch a
    `db_from_s3` job using GZIP compression, **do not**  trigger on All object
    create events` as this may cause two events to be sent and the job will run
    twice. Restrict the event type to `ObjectCreated:Put` only. This is due to
    the hidden copy operation lava must perform to set the correct content
    encoding on the source S3 object.

#### Enabling the Postgres RDS Copy Extension

To enable the
[aws_s3.table_import_from_s3](https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/PostgreSQL.Procedural.Importing.html)
copy extension follow the AWS instructions.

It is also necessary to allow the database users who will be performing
copy operations to access the extension, thus:

```sql
GRANT USAGE ON SCHEMA aws_s3 TO <USER>;
GRANT EXECUTE ON FUNCTION aws_s3.table_import_from_s3
    (
        table_name text,
        column_list text,
        options text,
        bucket text,
        file_path text,
        region text,
        access_key text,
        secret_key text,
        session_token text
        )
    TO <USER>;
```

#### Postgres RDS/Aurora Examples

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
    "db_conn_id": "pg-rds-conn-01",
    "s3_conn_id": "s3-conn-01",
    "bucket": "my-bucket",
    "key": "a/b/data.csv",
    "schema": "custardclub",
    "table": "membership",
    "mode": "truncate",
    "args": [
      "FORMAT CSV",
      "HEADER"
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
