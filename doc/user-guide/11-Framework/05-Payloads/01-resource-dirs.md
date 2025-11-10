
### Resource Directories

Directories directly under `lava-payloads` with names ending in `.rsc` or `.raw`
are static resource directories that contain no active job components but are
uploaded to the payloads area in S3 for consumption by lava jobs as required.

Directories ending in `.rsc` will have the contents Jinja rendered at
build/deploy time using the specified environment configuration file.

Directories ending in `.raw` are not Jinja rendered.

In either case, the directory structure is replicated in the project payload
area in S3 under the `prefix.payload` item from the environment configuration.
Symbolic links are followed as part of the process.

Note that the lava worker will completely ignore these areas in S3. It is up to
individual jobs to download the contents as required. For situations where
static resources need to be accessed locally by a job, it may be more
appropriate to place them directly in the `.pkg` or `.docker` directory so
that they are included in the job payload.

An element `my-file` from a resource directory `xyz.rsc` can be referenced in a
job specification thus:

```
{{ realm.s3_payloads }}/<{ prefix.payload }>/xyz.rsc/my-file
```
