
## Lava Schema Utility { data-toc-label="lava-schema" }

The **lava-schema** utility performs deep schema validation for lava DynamoDB
specification objects.

??? "Usage"

    ```bare
    usage: lava-schema.py [-h] [-d] [-r REALM] [-s DIRNAME]
                          [-t {job,s3trigger,connection}] [-v]
                          [SPEC ...]

    Deep schema validation for lava DynamoDB specification objects.

    positional arguments:
      SPEC                  If specified, specifications are read directly from
                            DynamoDB and any SPEC arguments are treated as GLOB style
                            patterns that the ID of the specifications must match. If
                            the -d / --dynamodb option is not specified, JSON formatted
                            lava object specifications are read from the named files.

    optional arguments:
      -h, --help            show this help message and exit
      -d, --dynamodb        Read lava specifications from DynamoDB instead of the local
                            file system. The lava realm must be specified, either via
                            the -r / --realm option or the LAVA_REALM environment
                            variable.
      -r REALM, --realm REALM
                            Lava realm name. If not specified, the environment variable
                            LAVA_REALM will be used. If --d / --dynamodb is specified,
                            a value must be specified by one of these mechanisms.
      -s DIRNAME, --schema-dir DIRNAME
                            Directory containing lava schema specifications. Default is
                            /usr/local/lib/lava/lava/lib/schema.
      -t {job,s3trigger,connection}, --type {job,s3trigger,connection}
                            Use the schema appropriate to the specified lava object
                            type. Options are job, s3trigger, connection. The default
                            is job.
      -v, --verbose         Print results for all specifications. By default, only
                            validation failures are printed.
    ```

**Lava-schema** can read specifications directly from DynamoDB or from the local
file system. The latter is useful to check the install components produced in
the `dist` directory by a [lava job framework](#the-lava-job-framework) project.

Whereas [lava-check](#lava-check-utility) is focused on basic configuration
management hygiene, **lava-schema** is focused on strict compliance with
lava [DynamoDB table specifications](#dynamodb-tables) using detailed
[JSON Schema](https://json-schema.org) specifications. (They may merge at some
point.)

### Lava-schema vs Lava Worker Validation

As of v7.1.0 (Pichincha), deep schema validation only manifests in the
**lava-schema** utility. The lava worker doesn't use this. Instead, it uses
its traditional process of checking just enough to validate that it
can try to run the job.

This will change in a future release and the worker will also perform deep
schema validation of the fully resolved [augmented job
specification](#the-augmented-job-specification) and the other [DynamoDB object
types](#dynamodb-tables) at run-time. Malformed jobs that could run under the
current validation process will be rejected outright.

!!! note "I'm from the Government and I'm here to help you."

Commonly observed configuration errors that the lava worker will tolerate but
**lava-schema** will not include:

*   **Malformed action specifications**    
    These don't prevent the job from running but the malformed actions will
    fail, potentially causing operational issues or unreported errors.

*   **Optional fields in the wrong place**    
    For example, the `timeout` parameter of [exe](#job-type-exe) jobs
    occasionally pops up at the top level of the job specification instead of
    within the job `parameters`. The lava worker will silently ignore the
    incorrectly placed `timeout` and do its best to run the job -- with the
    default timeout.

*   **Imaginary fields**    
    For example, the [sqlc](#job-type-sqlc) and [sqlv](#job-type-sqlv) job types
    support a `timeout` parameter but the [sql](#job-type-sql) and
    [sqli](#job-type-sqli) jobs do not. If a job is migrated between these
    types, it's easy to miss the need to add / remove the `timeout` parameter.
    The lava worker will happily run the job -- with the default timeout.

*   **Incorrect parameter types**    
    For example, the `args` parameter of the [exe](#job-type-exe) job type
    expects a list of *strings* (although numbers are OK also). Booleans
    are not. In a YAML job specification file in a
    [lava job framework](#the-lava-job-framework) project, it is easy to mix up
    an argument value of `true` (boolean) with `"true"` (string). The first one
    will get presented to the job payload at run-time as `True` and the second
    one will get presented as `true`. This could be a problem.

*   **It will be alright on the night**    
    When the lava worker runs a job, it grabs the job specification from
    DynamoDB and then merges in any parameters received as part of the dispatch
    message to produce the fully resolved
    [augmented job specification](#the-augmented-job-specification). It's
    tempting to leave out of the job specification parameters that are going to
    be replaced at run-time anyway. Problem is, this can make it tricky to work
    out what the job will do just by looking at the job specification.
    **Lava-schema** will complain about this because when it does its static
    analysis, the job is malformed. The lava worker is happy because it gets
    everything required at run-time. DevOps folk are less than pleased with a
    partially specified job in DynamoDB that frustrates attempts to diagnose
    problems.    

    It's good practice to include a placeholder in the job specification for
    *every* parameter, global and state item the job requires, even if it's
    replaced at run-time.

### Caveats

Because of the way JSON Schema works, some of the error messages that occur when
non-compliance is detected can be rather obscure. It's not uncommon for a
single specification error to generate multiple error messages. Generally, the
error messages give a pretty good indication of what's wrong.

There are, possibly, (rare) occasions when its legitimate for a job
specification in DynamoDB to not comply with lava schema requirements but the
fully resolved [augmented job specification](#the-augmented-job-specification)
at run-time does comply.

Did I mention that this is rare?

Trying to think of a situation where this is good design practice ...

Still thinking ...

