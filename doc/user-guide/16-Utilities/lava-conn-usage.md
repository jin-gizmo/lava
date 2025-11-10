
## Lava-conn-usage Utility { data-toc-label="lava-conn-usage" }

The **lava-conn-usage** utility will find the job IDs of jobs that reference
specified connectors.

??? "Usage"

    ```bare
    usage: lava-conn-usage [-h] [--profile PROFILE] [-i] [-r REALM]
                           connector-glob [connector-glob ...]

    Find lava jobs that reference specified connectors.

    positional arguments:
      connector-glob        Report jobs that use connectors that match any of the
                            specified glob style patterns.

    optional arguments:
      -h, --help            show this help message and exit
      --profile PROFILE     As for AWS CLI.
      -i, --ignore-case     Matching is case insensitive.
      -r REALM, --realm REALM
                            Lava realm name. If not specified, the value of the
                            LAVA_REALM environment variable is used. A value must
                            be specified by one of these mechanisms.
    ```

!!! tip
    See also [Lava-job-activity Utility](#lava-job-activity-utility).

For example, the following will find job IDs that reference connectors with IDs
containing the string `redshift` using a glob-style pattern match:

```bash
lava-conn-usage -r my-realm '*redshift*'
```

This can then be used with the [lava-job-activity](#lava-job-activity-utility)
utility to estimate the load lava is placing on particular resources (e.g. a
database). See [Estimating Lava Load on a
Connection](#estimating-lava-load-on-a-connection).

!!! info
    Only connections referenced in parameters known by lava to hold connection IDs
    will be found.

