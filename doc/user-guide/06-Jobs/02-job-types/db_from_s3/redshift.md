
### Loading Data to Redshift

Loading to Redshift is done using the native Redshift
[COPY](https://docs.aws.amazon.com/redshift/latest/dg/r_COPY.html) command.
Data files contain structured, tabular data. All of the formats supported by
the [COPY](https://docs.aws.amazon.com/redshift/latest/dg/r_COPY.html) command
can be used, including:

* CSV files
* JSON files
* Compressed versions of the above.

For Redshift, it is generally better to use `truncate` mode rather than `delete`.

#### Redshift Specific Parameters

The `db_conn_id` parameter must point to a connection with a `type` of
[redshift](#connector-type-redshift) or
[redshift-serverless](#connector-type-redshift-serverless).

The `args` parameter must contain a list of Redshift
[COPY](https://docs.aws.amazon.com/redshift/latest/dg/r_COPY.html) options
appropriate for the data file. Most of the parameters supported by
Redshift [COPY](https://docs.aws.amazon.com/redshift/latest/dg/r_COPY.html),
including `MANIFEST`, can be used.

#### Redshift Examples

The following example shows loading of a data file to a table in `append` mode.
The table will be created with the given column specifications if it doesn't
already exist.

```json
{
  "description": "Copy data to the table 'custardclub.membership'",
  "dispatcher": "Sydney",
  "enabled": true,
  "job_id": "demo/copy-mytable",
  "owner": "demo@somewhere.com",
  "parameters": {
    "db_conn_id": "redshift-conn-01",
    "s3_conn_id": "s3-conn-01",
    "bucket": "my-bucket",
    "key": "a/b/data.csv.bz2",
    "schema": "custardclub",
    "table": "membership",
    "mode": "truncate",
    "args": [
      "BLANKSASNULL",
      "BZIP2",
      "CSV",
      "EMPTYASNULL",
      "IGNOREHEADER 1",
      "MAXERROR 0",
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
