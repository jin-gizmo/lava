
## Lava Worker Status Utility { data-toc-label="lava-ws" }

The **lava-ws** utility displays worker status information based on the worker
SQS queues (queue depths, worker backlog etc.).

??? "Usage"

    ```bare
    usage: lava-ws [-h] [-f FORMAT] [-l] -r REALM [-w WORKER] [-v]

    Get status info about lava workers.

    optional arguments:
      -h, --help            show this help message and exit
      -f FORMAT, --format FORMAT
                            Output table format (see below). The formats supported
                            by tabulate (https://pypi.org/project/tabulate/) can
                            be used. The default is fancy_grid.
      -l                    Show more information. Repeat up to 2 times to get
                            more details.
      -r REALM, --realm REALM
                            Lava realm name.
      -w WORKER, --worker WORKER
                            Lava worker name prefix. If not specified, report on
                            all workers in the realm (assumes lava standard queue
                            naming conventions).
      -v, --version         show program's version number and exit

    output columns:
      BCKAVG   Average worker backlog in the last 15 minutes
      BCKMAX   Maximum worker backlog in the last 15 minutes
      BCKNOW   Current backlog
      DELAVG   Average run delay in the last 15 minutes
      DELMAX   Maximum run delay in the last 15 minutes
      EC2      Number of running EC2 instances
      EC2TYPE  EC2 instance type
      MSGS     Messages visible
      NVIS     Messages not visible
      QUEUE    SQS queue name
      RET      Message retention period
      VIS      Visibility timeout

    output formats:
      fancy_grid  fancy_outline   github           grid       html        jira
      latex       latex_booktabs  latex_longtable  latex_raw  mediawiki   moinmoin
      orgtbl      pipe            plain            presto     pretty      psql
      rst         simple          textile          tsv        unsafehtml  youtrack
    ```

Unlike **lava-ps**, which displays worker process information, **lava-ws** does
not need to run on the worker host.
