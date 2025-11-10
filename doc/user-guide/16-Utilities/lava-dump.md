## Lava Dump Utility { data-toc-label="lava-dump" }

**Lava-dump** performs a bulk extract of data from a single table to a local
directory. It can extract all entries with keys that match any of a list of GLOB
style patterns. By default, all entries are extracted.

??? "Usage"

    ```bare
    usage: lava-dump [-h] [-d DIR] [--profile PROFILE] [-i] [-n] [-r REALM] [-q]
                     [-t TABLE] [-y]
                     [glob-pattern [glob-pattern ...]]

    Extract lava configurations from DynamoDB and dump them to files.

    positional arguments:
      glob-pattern          Only extract items with keys that match any of the
                            specified glob style patterns. This test is inverted by
                            the -n / --not-match option.

    optional arguments:
      -h, --help            show this help message and exit
      -d DIR, --dir DIR     Store files in the specified directory, which will be
                            created if it does npt exist. Defaults to the current
                            directory.
      --profile PROFILE     As for AWS CLI.
      -i, --ignore-case     Matching is case insensitive.
      -n, --not-match       Only extract items with keys thay do not match any of
                            the specified glob patterns.
      -r REALM, --realm REALM
                            Lava realm name. This is required for all tables
                            except the realms table.
      -q, --quiet           Quiet mode.
      -t TABLE, --table TABLE
                            Extract from the specified table. This can be one of
                            jobs, connections, s3triggers (or triggers) or realms.
                            Any unique initial sequence is accepted.
      -y, --yaml            Dump items in YAML format. The default is JSON.
    ```

As well as being useful for backup, it is also useful for importing existing
items into the [lava job framework](#the-lava-job-framework).

See also [lava-backup](#lava-backup-utility).
