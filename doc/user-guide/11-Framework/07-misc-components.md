
## Miscellaneous Components

Lava jobs sometimes require other components that may, or may not, be deployed
as part of a job but which don't naturally belong in the lava payloads area in
S3.

For example, jobs may require some tables to be pre-created before the job runs.
The SQL to create the tables would be one such miscellaneous component. Another
example might be
[JSONPath](https://docs.aws.amazon.com/redshift/latest/dg/copy-usage_notes-copy-from-json.html)
files for a Redshift COPY operation for JSON data.

These components can be placed in the `misc` (miscellaneous) directory.

Any SQL scripts (`*.sql`) placed in the `misc` directory are
[Jinja](https://jinja.palletsprojects.com/) rendered at build/deploy time into
the `dist` directory using the specified environment configuration file, in the
same way as the DynamoDB table specifications.

By default, no other build or installation action is performed for anything in
the `misc` directory.

!!! info
    Do not edit `misc/Makefile` as this file will be replaced in the event of
    a framework update.

If some additional build or installation action is
required, the appropriate means to achieve this is to create a custom makefile
`Makefile.local`. This will be detected by the framework and invoked. This
makefile must implement the following targets, although they don't have to
do anything if not required:

*   dist
*   pre-install
*   install
*   uninstall.

The recommended approach is to copy the file `misc/Makefile.local.sample` to
`misc/Makefile.local` and customise as required.
