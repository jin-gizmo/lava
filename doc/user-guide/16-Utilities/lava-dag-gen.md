
## Lava DAG Generator { data-toc-label="lava-dag-gen" }

The **lava-dag-gen** utility generates a DAG specification for lava
[dag](#job-type-dag) jobs from a dependency matrix. It is
provided as part of the standard lava worker installation and is also included
in the `bin` directory with the
[lava job framework](#the-lava-job-framework). The lava job
framework also provides support for using the utility to automatically generate
DAGs at build time.

??? Usage

    ```bare
    usage: lava-dag-gen [-h] [-c] [-g GROUP] [-o] [-p PREFIX] [-r REALM] [-w KEY]
                        [--table TABLE] [-y]
                        source

    Generate a DAG specification for lava dag jobs from a dependency matrix.

    positional arguments:
      source                Source data for the DAG dependency matrix. CSV, Excel
                            XLSX files and sqlite3 files are supported. The
                            filename suffix is used to determine file type. If the
                            value is not a recognised file type, it is assumed to
                            be a lava database connection ID. In this case the
                            lava realm must be specified via -r, --realm or the
                            LAVA_REALM environment variable. For CSV and Excel,
                            the first column contains successor job names and the
                            first row contains predecessor job names. Any non-
                            empty value in the intersection of row and column
                            indicates a dependency. For database sources, a table
                            with three columns (job_group, job, depends_on) is
                            required. The "job" and "depends_on" columns each
                            contain a single job name. The "depends_on" column may
                            contain a NULL indicating the "job" must be included
                            but has no dependency. There can be multiple rows
                            containing the same "job".

    optional arguments:
      -h, --help            show this help message and exit
      -c, --compact         Use a more compact form for singleton and empty
                            dependencies.
      -g GROUP, --group GROUP
                            Select only the specified group of source entries. For
                            CSV files, this is ignored. For Excel files, this
                            specifies the worksheet name and defaults to the first
                            worksheet. For sqlite3 files, this is used as a filter
                            value on the "job_group" column of the source table
                            and defaults to selecting all entries.
      -o, --order           If specified, just print one possible ordering of the
                            jobs instead of the DAG specification.
      -p PREFIX, --prefix PREFIX
                            Prepend the specified prefix to all job IDs.
      -r REALM, --realm REALM
                            Lava realm. Required if the DAG source is specified as
                            a lava connection ID. Defaults to the value of the
                            LAVA_REALM environment variable.
      -w KEY, --wrap KEY    Wrap the DAG specification in the specified map key.
      --table [SCHEMA.]TABLE 
                            Table name for database sources. Default is dag.
      -y, --yaml            Generate YAML output instead of JSON.

    ```

**Lava-dag-gen** can read the dependency information from any of the following:

*   An SQLite3 database or a database accessed via a lava
    [database connector](#database-connectors) in
    [columnar](#columnar-format) format.

*   A CSV (`*.csv`) or Excel (`*.xlsx`) file in [matrix](#matrix-format) format.
    
### Columnar Format

Dependency information in columnar format must contain the following three
columns (only):

|Column|Description|
|-|----------------|
|job_group|An arbitrary grouping label for sets of jobs.|
|job|The job ID of the successor job. If all the jobs in a DAG have a common prefix in the job ID, this can be omitted here and inserted at run-time in the [dag](#job-type-dag) job specification.|
|depends_on|The ID of a predecessor job on which the subject job depends. This may be empty/NULL if the job has no dependencies. Once again, a common prefix can be omitted.|

Each row contains a single predecessor/successor pair. If a job has multiple
predecessors, there will be multiple rows for that job.

Sample DDL for a database:

```sql
CREATE TABLE dag
(
    job_group  VARCHAR(50),
    job        VARCHAR(50) NOT NULL,
    depends_on VARCHAR(50)
);
```

### Matrix Format

In matrix format, the first column contains successor job names and the first
row contains predecessor job names. Any non-empty value in the intersection of
row and column indicates a dependency. Like so:

| Jobs | J1 | J2 | J3 | J5 |
| ---- | -- | -- | -- | -- |
| J1   |    |    | x  | x  |
| J2   |    |    |    |    |
| J4   | x  |    |    |    |
| J4   |    |    | x  |    |
| J5   |    |    |    |    |

This would result in the following dag payload:

```json
{
    "J1": [
        "J3",
        "J5"
    ],
    "J2": null,
    "J4": [
        "J1",
        "J3"
    ]
}
```

Note that `J5` doesn't require its own entry as it is present as a predecessor
of `J1` and has no predecessors of its own.

