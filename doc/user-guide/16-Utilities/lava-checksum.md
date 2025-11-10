## Lava Checksum Utility { data-toc-label="lava-checksum" }

The **lava-checksum** utility verifies, adds and updates checksums on entries in
the following [lava DynamoDB tables](#dynamodb-tables).

*   the [connections table](#the-connections-table)

*   the [jobs table](#the-jobs-table)

*   the [s3triggers table](#the-s3triggers-table).

*   the [realms table](#the-realms-table).

!!! note
    The checksums are intended for drift detection only. They are **not** a code
    signing mechanism and they are not cryptographically sealed.

??? "Usage"

    ```bare
    usage: lava-checksum [-h] [-f {txt,tty,html,md}]
                         [--hash-algorithm ALGORITHM]
                         [-i] [--profile PROFILE] [-r REALM] [-t TABLE] [-v]
                         [--version]
                         {check,add,update} ...

    Set and validate checksums on lava DynamdoDB entries.

    positional arguments:
      {check,add,update}
        check               Validate checksums.
        add                 Add missing checksums.
        update              Update existing checksums.

    options:
      -h, --help            show this help message and exit
      -f {txt,tty,html,md}, --format {txt,tty,html,md}
                            Output format. Default is "tty" if stdout is a
                            terminal and "txt" otherwise.
      --hash-algorithm ALGORITHM
                            Algorithm to use for checksums. Default is sha256.
      -i, --ignore-case     Matching of glob patterns is case insensitive.
      --profile PROFILE     As for AWS CLI.
      -r REALM, --realm REALM
                            Lava realm name. If not specified, the environment
                            variable LAVA_REALM must be set.
      -t TABLE, --table TABLE
                            Extract from the specified table. This can be one of
                            jobs, connections, s3triggers (or triggers) or realms.
                            Any unique initial sequence is accepted. The default
                            is "jobs".
      -v, --verbose         Increase verbosity. By default, only checksum errors,
                            updates etc are reported. Can be specified multiple
                            times.
      --version             show program's version number and exit
    ```

To get help on a sub-command, use `-h` / `--help` on the sub-command. e.g.

```bare
lava-checksum check --help
```

Key points to note:

*   The checksums are stored in the entry in the field `x-lava-chk`.

*   Checksum calculation ignores any field starting with `x-` or `X-`.

*   The [lava-job-framework](#the-lava-job-framework) generates compatible checksums
    when deploying entries to the tables.

*   The checksum structure and format are internal to lava and subject to change
    at the capricious whim of the developer. The **lava-checksum** utility will
    manage backward compatibility.

Arguments for the **lava-checksum** utility shown above must be placed before
the sub-command. Arguments specific to sub-command must be placed after the
sub-command.

Note:

*   The `add` sub-command will only add missing checksums and `update` will only
    update existing checksums.

*   If any table entries are modified, a ZIP file will be left in the current
    directory containing the entries before they were updated. Delete this
    manually if not required.

### Examples

```bash
# Check all of the jobs in realm "prod"
lava-checksum --realm prod --table jobs -vv check

# Add missing checksums to connections matching app/* in realm "prod"
lava-checksum --realm prod --table conn -vv update 'app/*'
```
