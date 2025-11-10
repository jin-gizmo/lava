
## Executable Jobs

Executable jobs are handled by [cmd](#job-type-cmd),
[exe](#job-type-exe), [pkg](#job-type-pkg)
and [docker](#job-type-docker) job types.

Executable scripts (bash, Python, Perl etc), as well as worker compatible
binaries, are fine for use in lava. The information in this section is
applicable to all of these.

For [Python based jobs](#python-executable-jobs), additional
capabilities are provided by direct access to the lava packages.

The run-time environment for executable jobs in lava is a conventional Linux
environment based on the worker on which the job runs.

For docker jobs, some details may depend on the nature of the container being
run. Refer to the chapter on [lava and docker](#lava-and-docker)
for more information.

The main peculiarities associated with lava based executable jobs are outlined
below.

### Executable Scripts

Lava relies on the *hashbang* line at the beginning of the script to determine
the appropriate interpreter in exactly the same way that a UNIX shell does.

!!! warning "Beware DOS"
    If the script has been edited on a DOS system, it is very likely that it
    will have DOS style CRLF line endings instead of UNIX style LF endings.
    This will prevent the hashbang line from being recognised and the job will
    fail.

### Handling of Temporary Files { data-toc-label="Temporary Files" }

Lava jobs are run in a temporary directory created by lava and deleted by lava
when the job exits. 

The `TMPDIR` environment variable is set for
[cmd](#job-type-cmd),
[exe](#job-type-exe) and [pkg](#job-type-pkg)
jobs to point within the private run area for the job rather than inheriting
the default system setting. This variable can be referenced explicitly in a
job. Alternatively, the
[mktemp(1)](https://www.gnu.org/software/autogen/mktemp.html)
command line utility or the Python
[tempfile](https://docs.python.org/library/tempfile.html) module can
be used as these will use `TMPDIR` if used correctly.

!!! info
    The following applies to Linux. Note that
    [macOS mktemp(1)](https://www.unix.com/man-page/osx/1/mktemp/) behaves very
    differently in a number of ways, including using of `TMPDIR`.

Typical usage in a shell is:

```bash
#!/bin/bash

# Create a temp file in our private job area
MY_TMP_FILE=$(mktemp)

# Create a temp directory in our private job area
MY_TMP_DIR=$(mktemp -d)

# Create a temp directory using a name template. The -t is critical here.
MY_TMP_DIR2=$(mktemp -d -t tmp-XXXXXX)
```

Typical usage in Python is:

```python
#!/usr/bin/env python3

import tempfile

# Create a tempfile. The file is open.
tmp_file_descriptor, tmp_file_name = tempfile.mkstemp()

# Create a temp directory.
tmp_dir_name = tempfile.mkdtemp()
```

While lava will clean these up when the job exits, it is still good practice for
jobs to clean up after themselves. Jobs should generally avoid creating
temporary objects in `/tmp` because lava will not clean these up and there are
no guarantees about availability of storage space in `/tmp`.

### Testing if Running in Lava

Sometimes it's necessary for an executable to test whether or not it is running
in lava. The easiest way to do this is to look for the presence of one of the
lava environment variables `LAVA_REALM` or `LAVA_JOB_ID`.

In a bash script, this would look like:

```bash
#!/bin/bash

if [ "$LAVA_REALM" != "" ]
then
    # We are in lava
    echo "I lava you"
else
    # We are not in lava
    echo "I don't lava you anymore"
fi
```

### Handling of stdin, stdout and stderr { data-toc-label="Stdin, stdout and stderr" }

For executable jobs, stdin is redirected from `/dev/null` while stdout and
stderr are captured and uploaded to the realm temporary area in S3 unless the
worker is running with the `--dev` option. In that case, stdout and stderr are
emitted locally on the worker.

### Exit Status

Lava assumes that a zero exit status indicates that the job has succeeded. This
will trigger any `on_success` job actions.

A non-zero exit status indicates to lava that the job has failed. This will
trigger any `on_fail` actions.


### Status and Error messages

Executable jobs running under lava should print useful status and error messages
to stdout and stderr, just as they should when running in any other environment.

In normal operation, lava will collect this and upload it to S3 and place a
pointer to it in the job
event record.

When the worker is running with the `--dev` option, stdout and stderr from the
job are emitted locally rather than being sent to S3. This can help with
development and debugging.

### Connection Handling for Executable Jobs { data-toc-label="Connections in Executable Jobs" }

Handling of connections to external resources is facilitated via small
executables created by lava to effect the connection. The path to the connector
executable is passed to the lava job executable as an environment variable.

The following example shows how this would be used in a shell script to access
a database connection, but the mechanism is generic and available to any
executable that can read environment variables and invoke an external program.

```bash
#!/bin/bash

# The following environment variables are set in the Lava exe job specification.
# The can be as many connections to different resources as is required.
#
# LAVA_CONN_AURORA01
#    Lava connector script for the "aurora01" database. The lava job spec must
#    have an "aurora01" connections entry.

# SQL to do something
SQL="...."

# Run a command line SQL client that is preconfigured for auto login.
$LAVA_CONN_AURORA01 --database=dbname -e "$SQL" > local-temp-file

# Now do something clever with the results.
```

[Python based executable jobs](#python-executable-jobs) have
additional options for handling connections by virtue of programmatic access to
the underlying lava connection manager.
