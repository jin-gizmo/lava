
## Lava Job Activity Utility { data-toc-label="lava-job-activity" }

The **lava-job-activity** utility queries the realm
[events table](#the-events-table) to generate an activity map of specified jobs
over a defined time period. This is useful to see when specified jobs are
running, particularly for event triggered jobs.

??? Usage

    ```bare

    usage: lava-job-activity [-h] [--profile PROFILE] [-q] -r REALM [-s START_DTZ]
                             [-e END_DTZ] [--status STATUS] [--dump FILE]
                             [--load FILE] [-i MINUTES]
                             [job-id ...]

    Lava event log query utility

    positional arguments:
      job-id                Retrieve records for the specified job-id. Required
                            unless --load is used. If used with --load, this acts
                            as a further filter on event records loaded from the
                            dump file.

    optional arguments:
      -h, --help            show this help message and exit
      --profile PROFILE     As for AWS CLI.
      -q, --quiet           Don't print progress messages on stderr.
      -r REALM, --realm REALM
                            Lava realm name.

    query arguments:
      -s START_DTZ, --start START_DTZ
                            Start datetime. Preferred format is ISO 8601. If a
                            timezone is not specified, UTC is assumed. When using
                            --load, the default is the value from the source file.
                            Otherwise, the default is the most recent midnight
                            (UTC).
      -e END_DTZ, --end END_DTZ
                            End datetime. Preferred format is ISO 8601. If a
                            timezone is not specified, UTC is assumed. When using
                            --load, the default is the value from the source file.
                            Otherwise the default is 24 hours after the start
                            time.
      --status STATUS       Only include events with the given status.

    dump / load arguments:
      --dump FILE           Dump the raw data into the specified file in JSON
                            format. The format is suitable for loading using the
                            --load option. If both --load and --store are used,
                            they must be different files.
      --load FILE           Load the raw data from the specified file instead of
                            reading it from DynamoDB. The file will have been
                            produced by a previous run using the --dump option.
                            This allows a set of data to be reprocessed without
                            re-extracting the same data.

    output arguments:
      -i MINUTES, --interval MINUTES
                            Aggregate job activity into intervals of the specified
                            duration (minutes). Stick to divisors or multiples of
                            60. Default is 10.
    ```

!!! tip
    See also [Lava-conn-usage Utility](#lava-conn-usage-utility).

The process of extracting data from the events table can be expensive in usage
of DynamoDB table read capacity. Hence the extraction process has two
optimisations:

1.  Specific job IDs must be requested. This enables full table scans to be
    avoided on the, often large, [events table](#the-events-table).

2.  The extracted event data can be stored in a JSON formatted *dump* file. This
    file can be read back in subsequent runs of the utility to alter other
    parameters, such as the aggregation granularity. See the **--dump** and
    **--load** arguments.

The output to stdout is a CSV file containing two tables:

1.  Run-seconds per time-slice by job ID

2.  Run-seconds per time-slice by lava worker.

For example, the following command will extract the data for a given day and
job ID. The output CSV will have activity sliced into 10 minute blocks. The raw
data is retained for further analysis:

```bash
lava-job-activity -r my-realm --start 2024-02-15T00:00:00+11:00 \
    --dump evdata.json job-id > job-10.csv
```

Each time-slice column in the output CSV will indicate for how many seconds that
job run within that time-slice (i.e. *run seconds*). This can be greater than
the number of seconds in the time-slice if the job ran more than once in that
slice.

The extracted data can be reprocessed into 4 hour time-slices by reusing the
dump file thus:

```bash
lava-job-activity -r my-realm --start 2024-02-15T00:00:00+11:00 \
    --dump evdata.json --interval 240 job-id > job-240.csv
```

The CSV file will contain information something like this:

| Job ID | 15/2/2024 0:00 | 15/2/2024 4:00 | 15/2/2024 8:00 | 15/2/2024 12:00 | 15/2/2024 16:00 | 15/2/2024 20:00 |
|--------|---------------:|---------------:|---------------:|----------------:|----------------:|----------------:|
| job-id | 288            | 348            | 376            | 335             | 287             | 344             |

| Worker | 15/2/2024 0:00 | 15/2/2024 4:00 | 15/2/2024 8:00 | 15/2/2024 12:00 | 15/2/2024 16:00 | 15/2/2024 20:00 |
|--------|---------------:|---------------:|---------------:|----------------:|----------------:|----------------:|
| core   | 288            | 348            | 376            | 335             | 287             | 344             |

!!! info
    It is important to keep and re-use dump files where possible, particularly
    when extracting data for a large number of job IDs. However, the dump file
    will only contain raw event data requested for the initial set of job IDs
    and time window. It is not possible to reuse data that wasn't extracted in
    the first place.

### Estimating Lava Load on a Connection { data-toc-label="Estimating Load on a Connection" }

Sometimes it's useful to estimate how much load lava is placing on a particular
resource (such as a database) over a defined time window. This can be done by
combining the **lava-job-activity** and [lava-conn-usage](#lava-conn-usage-utility)
utilities.

The following example will produce the time-slice view described above for all
jobs that reference connectors with IDs starting with `redshift`:

```bash
lava-job-activity -r my-realm --start 2024-02-15T00:00:00+11:00 \
    --dump evdata.json \
    $(lava-conn-usage -r my-realm 'redshift*') > conn-activity.csv
```

Note that this does not mean the connection was in active use at all times in
the activity window. Lava has no way of knowing that. It does give a proxy view
of load intensity.

