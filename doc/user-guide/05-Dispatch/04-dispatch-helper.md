
## The Dispatch Helper

The dispatch helper is an AWS Lambda function that provides a simplified
mechanism for an external component to dispatch a lava job. It accepts simple,
dispatch requests and constructs the necessary messages within the lava
environment to complete the dispatch process.

The dispatch helper can accept dispatch requests via the following mechanisms:

*   SNS

*   SQS

*   Amazon EventBridge

*   direct invocation.

The standard CloudFormation template will setup an SNS topic,
`lava-<REALM>-dispatch` and subscribe the dispatch helper lambda function to it.
Other SNS topics or SQS queues can be created and subscribed manually as
required.

Two request formats are accepted:

1.  [CLI-style format](#cli-style-dispatch-requests)

2.  [JSON format](#json-dispatch-requests).

![](img/dispatcher.svg)


### CLI-Style Dispatch Requests

The dispatch request message sent to the dispatch helper must be in the
following format:

```bash
# One or more lines like the following. Shell style comments and blank lines
# are ignored. Shell style lexing is applied.

<JOB_ID> [-d DURATION] [-g <GLOBAL>=<VALUE>] ... [-p <PARAM>=<VALUE> ] ... 

# ... or ...

<JOB_ID> [--delay DURATION] [--global <GLOBAL>=<VALUE>] ... [--param <PARAM>=<VALUE> ] ...
```

For example:

```bash
# Dispatch the job "my-job" with no parameters.
my-job

# Dispatch the job "my-job" with some additional parameters.
my-job -p timeout=20m -p flow=Pahoehoe -g planet=Mars -g name='Alba Mons'

# Dispatch the job "my-job" with a delay of 3 minutes
my-job -d 3m

```

This is one way to send a dispatch message via the helper:

```bash
# Get the topic ARN then ...
aws sns publish \
    --topic-arn "arn:aws:sns:us-west-2:0123456789012:lava-<REALM>-dispatch" \
    --message "my-job -p timeout=20m -p flow=Pahoehoe -g planet=Mars -g name='Alba Mons'"
```

#### Parameter and Global Specifications

When specifying parameters and globals, the name can be a simple name or a dot
separated hierarchical name. The dispatch helper will convert the names into a
matching JSON structure that is included in the dispatch message. When the lava
worker receives the dispatch message, it will merge this structure into the
corresponding parameter or globals structure extracted from the [jobs
table](#the-jobs-table).

For example, consider the following message sent to the dispatch helper:

```bash
my-job -p timeout=1h -p vars.location=Isabela -p vars.name="Sierra Negra" -g country=Equador
```

The dispatch message sent by the dispatch helper will contain the following.

```json
{
    "globals": {
        "country": "Equador"
    },
    "parameters": {
        "timeout": "1h",
        "vars": {
            "location": "Isabela",
            "name": "Sierra Negra"
        }
    }
}
```

If the job specification in the [jobs table](#the-jobs-table)
contains the following:

```json
{
    "globals": {
        "country": "Replaced at run time",
        "ocean": "Atlantic"
    },
    "parameters": {
        "action": "run away",
        "timeout": "20m",
        "vars": {
            "whatever": "This will be replaced"
        }
    }
}
```

then the final job specification used by the lava worker will be:

```json
{
    "globals": {
        "country": "Equador",
        "ocean": "Atlantic"
    },
    "parameters": {
        "action": "run away",
        "timeout": "1h",
        "vars": {
            "location": "Isabela",
            "name": "Sierra Negra"
        }
    }
}
```

Notice that the parameters and globals from the dispatch helper override
similarly named parameters and globals in the job specification, including, in
this case, the entire `vars` map in the parameters.

### JSON Dispatch Requests

JSON formatted dispatch requests must be in the following format:

```json
{
  "job_id": "...",
  "globals": {
    "g1": "...",
    "g2": "..."
  },
  "parameters": {
    "p1": "...",
    "p2": "..."
  },
  "delay": "<DURATION>"
}
```

The `job_id` element is mandatory. All other elements are optional. The values
for individual `globals` and `parameters` can be any supported JSON type (not
just strings as shown above).

The dispatch request can be sent to the dispatch help lambda as either:

*   The body of an SQS or SNS message

*   The payload of a direct lambda invocation

*   The content of an event message produced by Amazon EventBridge.

For example, the following sends a dispatch request directly to the dispatch
helper lambda using the AWS CLI.


```bash
# Send a dispatch request directly to the dispatch helper for realm <REALM>

aws lambda invoke --cli-binary-format raw-in-base64-out \
    --function-name lava-<REALM>-dispatch \
    --invocation-type Event \
    --payload '{"job_id": "my-job-id", "globals": {"g1": "GLOB1"}}' \
    /dev/stdout
```

See also
[Dispatching Jobs from Amazon EventBridge](#dispatching-jobs-from-amazon-eventbridge).
