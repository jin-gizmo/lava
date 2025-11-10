
## Lava SQL Utility { data-toc-label="lava-sql" }

The **lava-sql** utility provides a simple, uniform CLI across different
database types with connectivity managed by the lava connection subsystem.

??? "Usage"

    ```bare
    usage: lava-sql [-h] [--profile PROFILE] [-v] [-a NAME] [-b BATCH_SIZE]
                    [--format {csv,jsonl,html,parquet}] [--header] [-o FILENAME]
                    [--raw] [--transaction] -c CONN_ID [-r REALM] [--no-colour]
                    [-l LEVEL] [--log LOG] [--tag TAG] [--delimiter CHAR]
                    [--dialect {excel,excel-tab,unix}] [--doublequote]
                    [--escapechar CHAR] [--quotechar CHAR] [--quoting QUOTING]
                    [--sort-keys]
                    [SQL-FILE ...]

    Run SQL using lava database connections.

    positional arguments:
      SQL-FILE              SQL files. These can be local or in S3 (s3://...). If
                            not specified or "-", stdin is used.

    optional arguments:
      -h, --help            show this help message and exit
      --profile PROFILE     As for AWS CLI.
      -v, --version         show program's version number and exit
      -a NAME, --app-name NAME, --application-name NAME
                            Use the specified application name when connecting to
                            the database. Ignored for database types that don't
                            support this concept.
      -b BATCH_SIZE, --batch-size BATCH_SIZE
                            Number of records per batch when processing SELECT
                            querues. Default is 1024.
      --format {csv,jsonl,html,parquet}
                            Output format. Default is csv.
      --header              Print a header for SELECT queries (output format
                            dependent).
      -o FILENAME, --output FILENAME
                            Write output to the specified file which may be local
                            or in S3 (s3://...). If not specified, output is
                            written to stdout.
      --raw                 Don't split SQL source files into individual
                            statements. By default, an attempt will be made to
                            split each source file into individual SQL statements.
      --transaction         Disable auto-commit and run all SQLs in a transaction.

    lava arguments:
      -c CONN_ID, --conn-id CONN_ID
                            Lava database connection ID. Required.
      -r REALM, --realm REALM
                            Lava realm name. If not specified, the environment
                            variable LAVA_REALM must be set.

    logging arguments:
      --no-colour, --no-color
                            Don't use colour in information messages.
      -l LEVEL, --level LEVEL
                            Print messages of a given severity level or above. The
                            standard logging level names are available but debug,
                            info, warning and error are most useful. The Default
                            is info.
      --log LOG             Log to the specified target. This can be either a file
                            name or a syslog facility with an @ prefix (e.g.
                            @local0).
      --tag TAG             Tag log entries with the specified value. The default
                            is lava-sql.

    CSV format arguments:
      --delimiter CHAR      Single character field delimiter. Default |.
      --dialect {excel,excel-tab,unix}
                            CSV dialect (as per the Python csv module). Default is
                            excel.
      --doublequote         See Python csv.writer.
      --escapechar CHAR     See Python csv.writer. Escaping is disabled by
                            default.
      --quotechar CHAR      See Python csv.writer. Default is ".
      --quoting QUOTING     As for csv.writer QUOTE_* parameters (without the
                            QUOTE_ prefix). Default is minimal (i.e.
                            QUOTE_MINIMAL).

    JSONL format arguments:
      --sort-keys           Sort keys in JSON objects.

    ```

**Lava-sql** can run one or more queries in a transaction and also capture
output from `SELECT` queries in various formats, either to a local file or to
AWS S3.

!!! info
    Do not have more than one `SELECT` query in the batch unless you are
    deliberately trying to create a mess.

### CSV

Note that the default delimiter for `csv` format is the pipe symbol `|`, not a
comma. The original rationale for this was for consistency with the Redshift
`COPY` and `UNLOAD` commands. All I can say is that it seemed to make sense at
the time.

### HTML Format

The output data is encoded as an HTML table with a class of `lava-sql`. Only
the table HTML is produced to allow the output to be incorporated into a larger
HTML document. (i.e. no `HTML`, `BODY` tags etc.).

Values will be escaped as needed to ensure HTML correctness.

### JSONL Format

Each row of output data is encoded as a single line JSON formatted object.

### Parquet Format

Parquet compression will generally benefit from a larger batch size. The default
of 1024 is reasonable for many purposes but increasing it will often give a
smaller output file. Don't get carried away though. Each batch has to be held
entirely in memory.

A word of caution about the Parquet schema ... It's quite difficult to handle
schema inference in a predictable or consistent way, particularly with data
sourced via a DBAPI 2 connector as the *standard* does not provide any
consistency in how, or if, implementations signal type information in query
responses. The approach used by **lava-sql** is to let
[PyArrow](https://arrow.apache.org/docs/python/index.html) form an educated
guess based on the first record batch. This should be fine for most purposes.
