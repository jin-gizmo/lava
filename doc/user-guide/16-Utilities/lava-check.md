
## Lava Check Utility { data-toc-label="lava-check" }

The **lava-check** utility performs some basic health checks on DynamoDB table
entries.

??? "Usage"

    ```bare
    usage: lava-check [-h] [-c GLOB] [--profile PROFILE] [-r REALM] [-S] [-v]
                      [--no-colour] [-l LEVEL] [--log LOG] [--tag TAG]

    Check lava specifications for problems.

    options:
      -h, --help            show this help message and exit
      -c GLOB, --check GLOB
                            Run the health checks with names matching the given
                            glob patterns. Can be used multiple times. If not
                            specified, print a list of available checks.
      --profile PROFILE     As for AWS CLI.
      -r REALM, --realm REALM
                            Lava realm name. If not specified, the environment
                            variable LAVA_REALM must be set.
      -S, --no-suppress     Disable suppression of checks for specific DynamoDB
                            entries via the x-lava-nocheck field. By default
                            suppression of specific checks is permitted for some
                            check types.
      -v, --version         show program's version number and exit

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
                            is lava-check.
    ```

See also [lava-schema](#lava-schema-utility).

**Lava-check** supports the following checks:

|Check Type|Description|
|---|---------------|
|conmeta|Connection specs with missing metadata (e.g. description, owner).|
|jobjinja *|Job specs with Jinja rendering issues. This includes jobs that use globals for which there is no placeholder entry in the job specification, referred to as undeclared globals. While lava tolerates undeclared globals, it is good practice to declare them with a placeholder value.|
|jobmeta|Job specs with missing metadata (e.g. description, owner).|
|joborphan \*|Jobs with no recorded run events.|
|jobrepo \*|Job specs that don't appear to have an associated repo (no `x-lava-git-repo` field).|
|jobrsu \*|[redshift_unload](#job-type-redshift_unload) jobs with `insecure` set to `true`.|
|trigmeta|S3trigger specs with missing metadata (e.g. description, owner).|

The checks marked with a * can be
[suppressed](#suppressing-checks-for-specific-entries) on an entry specific basis.

!!! note
    The checks need to perform a full table scan on the relevant table. This is
    not usually a problem but something to remember. Performing multiple checks
    on a given table in a single invocation will only do a single table scan
    though.

Output is in markdown formatted tables on the assumption that these issues may
end up in a backlog somewhere for correction.

### Suppressing Checks for Specific Entries { data-toc-label="Suppressing Checks" }

Some check types can be suppressed for specific DynamoDB table entries by
including an `x-lava-nocheck` field in the table entry. The value is a string
identifying a single check type to suppress, or a list of such strings.

For example, the following would suppress the `joborphan` check for a given job
specification:

```json
{
  "job_id": "rarely-run-job",
  "x-lava-nocheck": "joborphan",
  ...
}
```

This would suppress the `joborphan` and `jobrsu` checks:

```json
{
  "job_id": "yet-another-job",
  "x-lava-nocheck": [
    "joborphan",
    "jobrsu"
  ],
  ...
}
```
