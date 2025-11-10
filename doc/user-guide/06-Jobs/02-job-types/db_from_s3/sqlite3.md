
### Loading Data to SQLite3

Loading to SQLite is done by lava performing direct data insertion. The files
to be loaded are copied from S3 to the lava worker node, decompressed on the fly
if required, and then inserted row by row into the database by lava.

!!! warning
    If using `TRUNCATE` or `DROP` mode, a `COMMIT` is done after the `TRUNCATE`
    / `DROP` but prior to loading of new data.

#### SQLite3 Specific Parameters

The `db_conn_id` parameter must point to a connection with a `type` of
[sqlite3](#connector-type-sqlite3).

The `schema` parameter *must* be set to `main` as SQLite3 has a very limited
notion of schemas.

The `args` parameter supports the following options. The CSV format related
options are linked directly to the Python `csv` module
[formatting parameters](https://docs.python.org/3.9/library/csv.html#csv-fmt-params).

|Option|Description|
|-|-------------------------------------------------------------|
|DELIMITER 'c'|As for the Python `csv` module [formatting parameters](https://docs.python.org/3.9/library/csv.html#csv-fmt-params).|
|DOUBLEQUOTE|Controls how instances of `QUOTECHAR` appearing inside a field should themselves be quoted. If the `DOUBLEQUOTE` option is present, the character is doubled. If not present, the `ESCAPECHAR` is used as a prefix to the `QUOTECHAR`.| 
|ESCAPECHAR 'c'|As for the Python `csv` module [formatting parameters](https://docs.python.org/3.9/library/csv.html#csv-fmt-params).|
|GZIP|Source data is compressed using gzip. The worker will decompress it on the fly for insertion.|
|HEADER|Ignore the first line in each data file.|
|MANIFEST|The S3 object will be treated as a [Redshift compatible manifest](https://docs.aws.amazon.com/redshift/latest/dg/loading-data-files-using-manifest.html) containing a list of actual data files to load.|
|QUOTECHAR 'c'|As for the Python `csv` module [formatting parameters](https://docs.python.org/3.9/library/csv.html#csv-fmt-params).|
|QUOTING 'style'|As for the Python `csv` module [QUOTE_*](https://docs.python.org/3.9/library/csv.html#csv.QUOTE_ALL) parameters (without the `QUOTE_` prefix). Default is `minimal` (i.e. `QUOTE_MINIMAL`). Case is not significant.|
