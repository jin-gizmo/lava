
## Jinja Rendering of Lava Framework Components { data-toc-label="Jinja Rendering" }


It is very important to create the lava job framework component specifications
in a way that is environment independent. This allows the same specification
file to generate deployable components for multiple target environments (e.g.
development, testing, production). The framework achieves this by placing all
environment specific parameters into a YAML configuration file in the `config`
directory and using [Jinja](https://jinja.palletsprojects.com/) rendering to
inject the environment parameters into the specifications at build/deploy time.

The cookiecutter will create an initial skeleton environment configuration file
that can be tailored as needed and copied as the basis for other environments.
Apart from a small number of variables required for the correct operation of the
project framework, configuration files have no predefined structure. The file
can contain whatever other variables are required for a given project.

!!! info
    Parameters in the configuration file should not use the `lava` key. This is
    reserved for use by lava itself.

Because lava specifications can contain Jinja markup intended for lava itself,
this build/deploy time rendering must use non-standard Jinja delimiters to
avoid a clash. For build/deploy time parameter injection, use the following
Jinja delimiters.

*   `<{...}>` instead of `{{...}}`

*   `<#...#>` instead of `{#...#}`

*   `<%...%>` instead of `{% %}`

### Built-in Rendering Variables

In addition to the parameters defined in the environment configuration file,
the following variables are also made available to the renderer.

|Name|Type|Description|
|----|----|----------------------------------------|
|env|str|The name of the configuration file (without the `.yaml` suffix).|
|jinja.ctime|str|Current local date/time in ctime(3) format.|
|jinja.datetime|str|Current local date/time in YYYY-mm-dd HH:MM:SS format.|
|jinja.iso\_datetime|str|Current date/time in ISO8601 format.|
|jinja.prog|str|Name of the rendering program.|
|jinja.templates|list[str]|A list of the files being rendered. For framework files, `jinja.templates[0]` will be the name of the YAML source file relative to the enclosing `lava-*` directory.|
|jinja.user|str|Current user name.|
|jinja.utc\_ctime|str|Current UTC date/time in ctime(3) format.|
|jinja.utc\_datetime|str|Current UTC date/time in YYYY-mm-dd HH:MM:SS format.|
|lava.aws.account|str|The AWS account ID.|
|lava.aws.arn()|function|Helper function to assist with constructing AWS ARNs for a limited range of AWS resource types. See below.|
|lava.aws.ecr\_uri|str|The base URI for the ECR registry. The repository name needs to be appended to get the repository URI.|
|lava.aws.region|str|The AWS region (e.g. `ap-southeast-2`).|
|lava.aws.user|str|The AWS user or role name (e.g. `user/fred`).|
|lava.dag()|function|A helper function for building [DAG payloads](#dag-payloads).|
|lava.realm|dict[str,\*]|The [realms](#the-realms-table) table entry for the target realm. e.g. `<{ lava.realm.s3_temp.split('/')[2] }>` is the realm temp bucket.|

The `lava.arn(service, resource)` function is a helper function to generate AWS ARNs. Mostly
these are required for specifying targets for
[Amazon EventBridge Rules](#creating-amazon-eventbridge-rules). The allowed
values for the `service` and `resource` arguments are:

|service|resource|
|-|-------|
|iam-role|The name of an IAM role.|
|lambda-function|The name of an AWS Lambda function.|
|log-group|The name of a CloudWatch log group.|
|sns-topic|The name of an SNS topic.|
|sqs-queue|The name of an SQS queue.|

For example, this will generate the ARN for the
[s3trigger](#dispatching-jobs-from-s3-events) Lambda function for the realm:

```
<{ lava.aws.arn('lambda-function', 'lava-' + realm + '-s3trigger') }>
```

### Jinja Template Factorisation { data-toc-label="Template Factorisation" }

In more complex projects, it is not uncommon to have several jobs or triggers
containing similar or repeated material. This material can be factored out into
reusable sub-templates that are included into the main component at build time.

If these reusable sub-templates are located in one of the `lava-*` directories
and have names ending in `.yaml` or `.json`, they must have names starting with
an underscore, or be in a subdirectory with a name starting with underscore,
otherwise the framework will attempt to process them as a complete specification
in their own right.

Jinja provides several mechanisms to facilitate such factorisation:

1.  [Template inheritance](#jinja-template-inheritance)

2.  [Template inclusion](#jinja-template-inclusion)

3.  [Template import](#jinja-template-import)

4.  [Template self-configuration](#jinja-template-self-configuration)

#### Jinja Template Inheritance

Template inheritance allows construction of a base skeleton template that
contains common elements and defines blocks that child templates can override.

It is the most complex of the factorisation methods. Refer to the
[Jinja documentation](https://jinja.palletsprojects.com) for details.

#### Jinja Template Inclusion

The Jinja
[include](https://jinja.palletsprojects.com/en/2.11.x/templates/#include)
statement is useful to include a sub-template and return the rendered contents
of that file into the current namespace. These sub-templates are rendered using
the environment configuration file in exactly same way as the main component
files. They can also receive variable values that are set in the parent file.

The sub-templates can be placed in a subdirectory of the relevant lava job
framework directory or in a common area elsewhere in the project tree. YAML
files that are not full specification files must have names beginning with
underscore or be in a subdirectory with a name beginning with an underscore if
located within one of the `lava-*` directories.

For example, consider the following s3trigger specification.

```yaml
description: "Process data received from source_a"
trigger_id: "<{ prefix.s3trigger }>/source_a"

enabled: true

job_id: "<{ prefix.job }>/process/source_a"

bucket: "<{ s3.bucket }>"
prefix: "source_a"

parameters:
  vars:
    bucket: "{{ bucket }}"
    key: "{{ key }}"
```

This is fine if there is only a single `source_a` that needs to be handled. If
new sources are added that have similar processing, the s3trigger specification
will be copied multiple times with common material.

An alternative approach is to create a new directory `lava-triggers/_common`
containing the following file `whatever.yaml`. This relies on the main template
to set the `source` variable.

```yaml
description: "Process data received from <{ source }>"
trigger_id: "<{ prefix.s3trigger }>/<{ source }>"

enabled: true

job_id: "<{ prefix.job }>/process/<{ source }>"

bucket: "<{ s3.bucket }>"
prefix: "<{ source }>"

parameters:
  vars:
    bucket: "{{ bucket }}"
    key: "{{ key }}"
```

The main s3trigger specification then becomes:

```yaml
# Set the source for the sub-template
# <% set source='source_a' %>

# Load the sub-template
# <% include '_common/whatever.yaml' %>
```

#### Jinja Template Import

Jinja2 allows variables (and macros) to be imported from other templates using
the [import](https://jinja.palletsprojects.com/en/2.11.x/templates/#import)
statement. This process is broadly similar to Python imports.

Imported templates don’t have access to the current template variables, just the
globals.

For example, consider the following file `vars.jinja`:

```jinja
<% set bucket='my-bucket' %>
```

This can be used in YAML template thus:

```yaml
# <% from 'vars.jinja' import bucket %>

bucket: "<{ bucket }>"
```

Alternatively:

```yaml
# <% import 'vars.jinja' as v %>

bucket: "<{ v.bucket }>"
```

Note that because `vars.jinja` does not end in `.yaml`, the framework will not
confuse it with a specification file.

### Jinja Template Self-Configuration { data-toc-label="Template Self-Configuration" }

The Jinja rendering process is aware of the name of the source file being
rendered and makes this name available for use in the rendering process as the
expression `jinja.templates[0]`. For example, if the source file is
`lava-jobs/dir/file.yaml`, this expression will have the value `dir/file.yaml`.

This allows the contents of the created DynamoDB object to be dependent on the
name of the file.

Here is a simple example of how this can be used to create a generic job that
avoids embedding specific configuration details.

```yaml
# Assume the name of this file is lava-jobs/my-db/my-schema/my-table/count.yaml
 
# Extract database, schema and table names:
# <% set db=jinja.templates[0].split('/')[0] %>
# <% set schema=jinja.templates[0].split('/')[1] %>
# <% set table=jinja.templates[0].split('/')[2] %>

# Now we can use these in our job spec

description: "Count rows in <{ schema }>.<{ table }> in database <{ db }>"
job_id: "<{ prefix.job }>/count/<{ db }>/<{ schema }>.<{ table }>"
type: sqli
owner: "<{ owner }>"

dispatcher: "<{ dispatcher.main }>"
worker: "<{ worker.main }>"
enabled: true

payload: "SELECT count(*) FROM <{ schema }>.<{ table }>"
parameters:
  # Lookup a table in the config file to convert db to a connector ID
  conn_id: "<{ db_conn_table[db] }>"
```

This is probably overkill for handling a single table in a single database.
However, if the same action is required for multiple tables, the same
specification can be copied without modification, provided the file naming
structure is setup correctly. Alternatively, symlinks can be used to avoid
multiple copies of the same specification. Like so:

```
lava-jobs
├── Makefile
├── README.md
├── _common
│   └── count.yaml
├── db1
│   ├── schema1
│   │   └── table1
│   │       └── count.yaml -> ../../../_common/count.yaml
│   └── schema2
│       └── table2
│           └── count.yaml -> ../../../_common/count.yaml
└── db2
    └── schema3
        └── table3
            └── count.yaml -> ../../../_common/count.yaml
```
