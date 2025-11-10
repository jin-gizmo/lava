
## Creating DynamoDB Items

The `lava-connections`, `lava-jobs` and `lava-triggers` directories will contain
the source for the lava specification components for the project. The source can
be either JSON (`*.json`) or YAML (`*.yaml`) files that will be converted into
JSON and pushed to the appropriate DynamoDB table as part of the [deployment
process](#installing-deployable-components). It is strongly
recommended to use YAML as it is easier to write, read and annotate with
comments.

There are samples for the various DynamoDB table entries available in the
[Lava Job Framework Samples](#lava-job-framework-samples)
section.

Existing lava configuration entries can be imported from the [DynamoDB
tables](#dynamodb-tables) using the
[lava-dump](#lava-dump-utility) utility. The resulting files will need
to be manually edited to remove realm specific settings and move those to the
environment configuration file(s).

### Jinja Rendering of DynamoDB Items { data-toc-label="Jinja Rendering of Items" }

Jinja rendering of lava framework components as part of the build and deploy
process is supported. See
[Jinja Rendering of Lava Framework Components](#jinja-rendering-of-lava-framework-components).


### Conditional Deployment of DynamoDB Items { data-toc-label="Conditional Deployment" }

In most cases, exactly the same inventory of components should be deployed to
all target environments, although the contents may be environment specific. In
some, limited, circumstances, some components may not need to be deployed to
some target environments.

The lava framework will skip deployment of a component if the built JSON
component contains only a `null` object. This is achieved by wrapping the YAML
source for the object in a Jinja conditional block like so:

```yaml
# <% if env in ('dev', 'uat') %>
description: Conditional job
job_id: maybe_yes_maybe_no
type: etc ...
# <% endif %>
```

When this job is built for the `dev` or `uat` environments, the resulting json
object will be non-null and hence the job will be installed. when it is built
for the `prod` environment, the contents will generate a `null` JSON object 
which will be skipped during installation.

The conditional logic can make use of any of the configuration information
made available when rendering the item, including the contents of the environment
configuration file.

### Examples

The following example shows an [sql](#job-type-sql) job
specification:

```yaml
# --------------------------------------
description: Sample SQL job
dispatcher: <{ dispatcher.none }>
enabled: true
job_id: <{ prefix.job }>/simple-sql
owner: <{ owner }>
payload: <{ prefix.payload }>/simple.sql
type: sql
worker: <{ worker.main }>

# Get the name of the job source file relative to lava-jobs dir.
x-srcfile: <{ jinja.templates[0] }>

# --------------------------------------
# Post job actions
# <% if on_fail %>
on_fail: <{ on_fail }>
# <% endif %>

# <% if on_success %>
on_success: <{ on_success }>
# <% endif %>

# --------------------------------------
parameters:
  conn_id: <{ conn.mydb }>
  vars:
    schema_name: <{ schema.staging }>
```

All of the values delimited by `<{...}>`, `<%...%>` will be obtained from
whichever environment configuration file is used at build/deploy time.

If the configuration file is:

```yaml
# --------------------------------------
# Lava environment configuration file

realm: "user01"
prefix:
  job: "app/demo"
  payload: "app/demo"
  s3trigger: "app/demo"
owner: "Fred"
worker:
  main: "core"
dispatcher:
  main: "Sydney"
  none: "--"
schedule:
  main: "--"

# --------------------------------------
# Connections
conn:
  mydb: redshift/dev

# --------------------------------------
# Post-job actions These can be safely removed if not needed.
on_fail:
  - action: email
    to: fred@somewhere.com
    subject: "ALARM: Job={{job.job_id}}@{{realm.realm}}"
    message: "Run {{job.run_id}}: {{result.error}}"

# --------------------------------------
# Custom variables.

schema:
  staging: public
```

The final job will look like this:

```json
{
    "description": "Sample SQL job",
    "dispatcher": "--",
    "enabled": true,
    "job_id": "app/demo/simple-sql",
    "on_fail": [
        {
            "action": "email",
            "message": "Run {{job.run_id}}: {{result.error}}",
            "subject": "ALARM: Job={{job.job_id}}@{{realm.realm}}",
            "to": "fred@somewhere.com"
        }
    ],
    "owner": "Fred",
    "parameters": {
        "conn_id": "redshift/dev",
        "vars": {
            "schema": "public"
        }
    },
    "payload": "app/demo/simple.sql",
    "type": "sql",
    "worker": "core"
}
```
