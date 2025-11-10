
### Loading Data to Postgres

Loading to Postgres is done using a [client side
COPY](https://www.postgresql.org/docs/10/sql-copy.html). The files to be loaded
are copied from S3 to the lava worker node, decompressed if required, and then
copied to the database via the client.

While this will work for Postgres RDS/Aurora, it will be much slower than a
direct S3 copy as described in [Loading Data to Postgres
RDS](#loading-data-to-postgres-rds).

Moreover, if multiple files are to be loaded (e.g. when using a manifest), the
files are processed sequentially. This can make the whole operation rather slow.
If large amounts of data need to be loaded, it is recommended to implement a
custom loading process.

Loading of each individual file is subject to a timeout which is set via the
[PG\_COPY_TIMEOUT](#configuration-for-db_from_s3-jobs)
configuration variable. This can be set at the worker or realm level.

!!! warning
    If using `TRUNCATE` or `DROP` mode, a `COMMIT` is done after the `TRUNCATE`
    / `DROP` but prior to loading of new data.

#### Postgres Specific Parameters

The `db_conn_id` parameter must point to a connection with a `type` of
[postgres](#connector-type-postgres) or
[psql](#connector-type-psql).

Use with
[postgres-aurora](#connector-type-postgres-aurora) or
[postgres-rds](#connector-type-postgres-rds)
will work but is not recommended.

The worker uses its own credentials to copy the files from S3 to local storage.
The `s3_conn_id` and `s3_iam_role` parameters are not used.

The `args` parameter must contain a list Postgres
[COPY](https://www.postgresql.org/docs/10/sql-copy.html) options. 

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
|GZIP|Source data is compressed using gzip. The worker will decompress it prior to loading.|
|MANIFEST|The S3 object will be treated as a [Redshift compatible manifest](https://docs.aws.amazon.com/redshift/latest/dg/loading-data-files-using-manifest.html) containing a list of actual data files to load.|
