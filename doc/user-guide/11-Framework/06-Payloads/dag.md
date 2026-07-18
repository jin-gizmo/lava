
### DAG Payloads

The payload for [dag](#job-type-dag) jobs is a map
representing job dependencies. The details can be included directly in the job
specification.  The job framework also provides support for generating this
map at build time via the following:

*   The [lava-dag-gen](#lava-dag-generator) utility which is
    provided in the job framework `bin` directory.

*   A Jinja function, `lava.dag()`, that calls this utility to generate and
    interpolate a DAG payload at build time.

!!! note
    The lava framework cannot easily tell if a job using the `lava.dag()`
    function needs to be rebuilt as it may depend on external data. Hence, the
    framework will always rebuild job specifications that use this function.

This following example shows how to use the Jinja function:

```yaml
description: A daggy job

type: dag

job_id: "<{ prefix.job }>/dag/demo"
worker: "<{ worker.main }>"
enabled: true
owner: "<{ owner }>"

parameters:
  workers: 2

# Generate the dag payload by reading the first tab in Excel file dag.xlsx
payload:  "<{ lava.dag('dag.xlsx'}>"
```

The first (positional) argument to the `lava.dag()` function corresponds to the
`source` argument of the
[lava-dag-gen](#lava-dag-generator) utility.

The `lava.dag()` function also supports keyword arguments that match the
`--option value` command line options of the 
[lava-dag-gen](#lava-dag-generator) utility, although not all of
these are useful in a lava framework job specification.

The following example shows how to generate the dag payload by reading
dependencies from a database using a lava connector:

```yaml
description: A daggy job

type: dag

job_id: "<{ prefix.job }>/dag/demo"
worker: "<{ worker.main }>"
enabled: true
owner: "<{ owner }>"

parameters:
  workers: 2

# Generate the dag payload by reading a database table. Note that the realm
# value from the framework configuration file is used.
payload: "<{ lava.dag('a_conn_id', group='a_batch', table='a_schema.dags', realm=realm) }>"
```

Note that the `lava.dag()` function actually returns a JSON formatted string.
This works in a YAML source file because valid JSON is also valid YAML. Neat eh?

!!! info
    Using the `lava.dag()` function with a lava database connector requires that
    the lava package is installed in the framework virtual environment.

