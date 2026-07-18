
### Loading Data to Oracle

Loading to Oracle is done by lava performing direct data insertion. The files
to be loaded are copied from S3 to the lava worker node, decompressed on the fly
if required, and then inserted row by row into the database by lava.

!!! warning
    If using `TRUNCATE` or `DROP` mode, a `COMMIT` is done after the
    `TRUNCATE` / `DROP` but prior to loading of new data.

#### Oracle Specific Parameters

The `db_conn_id` parameter must point to a connection with a `type` of
[oracle](#connector-type-oracle).

The `args` parameter supports the following options. The CSV format related
options are linked directly to the Python `csv` module
[formatting parameters](https://docs.python.org/library/csv.html#csv-fmt-params).

|Option|Description|
|-|-------------------------------------------------------------|
|DELIMITER 'c'|As for the Python `csv` module [formatting parameters](https://docs.python.org/library/csv.html#csv-fmt-params).|
|DOUBLEQUOTE|Controls how instances of `QUOTECHAR` appearing inside a field should themselves be quoted. If the `DOUBLEQUOTE` option is present, the character is doubled. If not present, the `ESCAPECHAR` is used as a prefix to the `QUOTECHAR`.| 
|ESCAPECHAR 'c'|As for the Python `csv` module [formatting parameters](https://docs.python.org/library/csv.html#csv-fmt-params).|
|GZIP|Source data is compressed using gzip. The worker will decompress it on the fly for insertion.|
|HEADER|Ignore the first line in each data file.|
|MANIFEST|The S3 object will be treated as a [Redshift compatible manifest](https://docs.aws.amazon.com/redshift/latest/dg/loading-data-files-using-manifest.html) containing a list of actual data files to load.|
|NLS_*|See [Oracle NLS Session Parameters](#oracle-nls-session-parameters) below.|
|QUOTECHAR 'c'|As for the Python `csv` module [formatting parameters](https://docs.python.org/library/csv.html#csv-fmt-params).|
|QUOTING 'style'|As for the Python `csv` module [QUOTE_*](https://docs.python.org/library/csv.html#csv.QUOTE_ALL) parameters (without the `QUOTE_` prefix). Default is `minimal` (i.e. `QUOTE_MINIMAL`). Case is not significant.|

#### Oracle NLS Session Parameters

!!! note
    New in v8.3 (Mauna Loa).

Oracle supports a number of session parameters that can be useful in the context
of data loading. These all have names of the form `NLS_*` and can be set in the
`args` parameter of the job specification. For example:

```json
    {
        "args": {
            "NLS_DATE_FORMAT": "YYYY-MM-DD"
        }
    }
```

!!! info
    Lava will not accept an NLS parameter value containing single quotes.

The most useful session parameters for the [db_from_s3](#job-type-db_from_s3)
job type are those that relate to [date and time formats](https://docs.oracle.com/en/database/oracle/oracle-database/26/nlspg/setting-up-globalization-support-environment.html#GUID-2796FB20-5F58-4471-B28D-748C514DEE32).

| Parameter | Description | Example |
|-|-|-|
|NLS_DATE_FORMAT|Format used to coerce strings to the `DATE`.|`YYYY-MM-DD`|
|NLS_TIMESTAMP_FORMAT | Format used to coerce strings to `TIMESTAMP` and `TIMESTAMP WITH LOCAL TIME ZONE`. | `YYYY-MM-DD HH:MI:SS.FF` |
|NLS_TIMESTAMP_TZ_FORMAT| Format used to coerce strings to `TIMESTAMP WITH TIME ZONE`.| `YYYY-MM-DD HH:MI:SS.FF TZH:TZM` |

!!! warning
    Avoid using `NLS_TIME_FORMAT` and `NLS_TIME_TZ_FORMAT`. They are
    undocumented and appear to be used for Oracle internal purposes only.

