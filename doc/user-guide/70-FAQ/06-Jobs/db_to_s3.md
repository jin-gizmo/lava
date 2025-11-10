
### db_to_s3

#### There is no db_to_s3 job type. What should I do instead?

Yes. Sorry about that.

There are a number of alternatives.

For Redshift, use [redshift_unload](#job-type-redshift_unload) which is
optimised to extract data from Redshift efficiently.

For other database types, the [lava-sql](#lava-sql-utility) utility can cover
many use cases. It can extract data from all supported database types into CSV,
JSONL and Parquet format. It can be called directly from within the payload of
[exe](#job-type-exe), [pkg](#job-type-pkg) and [docker](#job-type-docker) jobs.

It can also be used directly in a [cmd](#job-type-cmd) job as a DIY version of a
`db_to_s3` job. This is what such a job might look like in the YAML format
supported by the [lava job framework](#the-lava-job-framework):

```yaml
description: Ersatz db_to_s3 type of job

type: cmd

job_id: <{ prefix.job }>/ersatz-db-to-s3

worker: <{ worker.main }>
enabled: true
owner: <{ owner }>

payload: >-
  /bin/sh -c
  "
  echo 'SELECT a, b, c FROM my_schema.my_table' |
  lava-sql
  --format csv
  --header
  --conn-id '<{ db.conn_id }>'
  --output '{{ realm.s3_temp }}/{{ job.job_id }}/output.csv'
  -
  "

event_log: Output file is {{ realm.s3_temp }}/{{ job.job_id }}/output.csv

```

Note the final `-` argument to [lava-sql](#lava-sql-utility) tells it to
read the query from stdin.

We can also load the query from S3 instead of embedding it in the job, thus:

```yaml
description: Ersatz db_to_s3 type of job

type: cmd

job_id: <{ prefix.job }>/ersatz-db-to-s3

worker: <{ worker.main }>
enabled: true
owner: <{ owner }>

payload: >-
  /bin/sh -c
  "
  lava-sql
  --format csv
  --header
  --conn-id '<{ db.conn_id }>'
  --output '{{ realm.s3_temp }}/{{ job.job_id }}/output.csv'
  '{{ realm.s3_payloads }}/<{ prefix.payload }>/xyz.rsc/query.sql'
  "

event_log: Output file is {{ realm.s3_temp }}/{{ job.job_id }}/output.csv
```
