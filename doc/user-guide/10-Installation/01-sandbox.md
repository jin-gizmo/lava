
## The Lava Sandbox

[MiniStack]: https://ministack.org
[StackPort]: https://github.com/DaviReisVieira/stackport
[DockerDesktop]: https://docs.docker.com/desktop/
[Mailpit]: https://mailpit.axllent.org))
[VercelEmulate]: https://github.com/vercel-labs/emulate)
[LavaGui]: https://github.com/jin-gizmo/lava-gui#lava-gui
[DockerCompose]: https://docs.docker.com/compose/
[Boto3PutParameter]: https://docs.aws.amazon.com/boto3/latest/reference/services/ssm/client/put_parameter.html

The **lava sandbox** is a complete, functional lava environment that runs
locally in docker with a single CLI command. No AWS entanglement. No AWS costs.
It is ideal for local development, testing and experimentation.

!!! note
    The lava sandbox is new in v8.4.0 (Kohala)

!!! info
    The lava sandbox was developed with [Docker Desktop][DockerDesktop].
    Your mileage may vary with the various alternatives. [^Docker-Alternatives]

[^Docker-Alternatives]: There are no philosophical objections to Docker Desktop
    alternatives, but neither is supporting them a priority. If anyone is
    inspired to take this on, raise an issue to discuss.

### Quick Start

```bash
curl -O https://raw.githubusercontent.com/jin-gizmo/lava/refs/heads/master/docker/sandbox/docker-compose.yaml

# Run the lava sandbox
docker compose up -d 
```

This will create some docker containers:

1.  `lava-sandbox-realm`: An AWS emulation environment based on
    [MiniStack][MiniStack]. [^MiniStack] It contains all the
    required AWS components to host a lava realm named `sandbox`. It also has a
    few benign lava jobs pre-loaded as samples. The AWS endpoint URL for the
    emulated environment is `http://localhost:4566`.

2.  `lava-sandbox-worker`: A lava worker pointing at `lava-sandbox-realm`. The
    worker name is `dev`.

3.  `lava-sandbox-console`: A basic AWS web browser console based on
     [StackPort][StackPort], also pointing at `lava-sandbox-realm`. It is
     available at <http://localhost:8086/>{target="_blank"}

4.  `lava-sandbox-mail`: A test email server based on [Mailpit][Mailpit] [^Mailpit].
    Among other things, this provides an SMTP service with a nice GUI available
    at <http://localhost:8025>. The sandbox includes a lava connector
    `sandbox/email/smtp` that connects to this.

[^MiniStack]: [MiniStack][MiniStack] is an excellent replacement for
    the once-popular LocalStack, which is now proprietary. MiniStack is a very
    active project and the team turns around bug reports very quickly.


[^Mailpit]: [Mailpit][Mailpit] is a great piece of kit. Not only is it an
    excellent SMTP emulator, it also has a bunch of other capabilities, such as
    spam testing, HTML compatibility checking for lots of different mail
    clients, etc.

Open the *AWS* console at <http://localhost:8086/>{target="_blank"}.
The `lava.sandbox.jobs` DynamoDB table shows the pre-installed demo jobs.
To run one of the jobs, grab the job ID for one of the jobs, go to the SNS
console panel and send the job ID as a message on the `lava-sandbox-dispatch`
topic. Check the `lava.sandbox.events` table for the result.

You can also see worker activity in the logs for the `lava-sandbox-worker`
container.

```
❯ docker logs -f lava-sandbox-worker
lava-worker: MainThread: Worker ready ...
lava-worker: worker-00: Job demo/cmd/hello-world (4ac406df-fcec-4da5-8407-dbbcd3836126): Starting
lava-worker: worker-00: Job demo/cmd/hello-world (4ac406df-fcec-4da5-8407-dbbcd3836126): Running iteration 1
lava-worker: worker-00: Job demo/cmd/hello-world (4ac406df-fcec-4da5-8407-dbbcd3836126): Complete
```

When you're done:

```bash
docker compose down -v
```

### AWS Tools and the Sandbox  { data-toc-label="AWS tools & the Sandbox" }

The [MiniStack][MiniStack] based `lava-sandbox-realm` container is an
accomplished AWS emulator.  Standard AWS tools, and the [lava GUI][LavaGui] work
well with the environment. The recommended approach is to create an AWS profile
for the sandbox by adding the following content to the standard AWS
configuration files.

=== "~/.aws/config"
    ```ini
    # Lava sandbox (Ministack)
    [profile sandbox]
    region = us-east-1
    endpoint_url = http://localhost:4566
    ```

=== "~/.aws/credentials"
    ```ini
    # Lava sandbox (Ministack)
    [sandbox]
    aws_access_key_id = test
    aws_secret_access_key = test
    ```

For the AWS CLI:

```bash
export AWS_PROFILE=sandbox
```

```
❯ aws sts get-caller-identity
{
    "UserId": "123456789012",
    "Account": "123456789012",
    "Arn": "arn:aws:iam::123456789012:root"
}
```

### The Lava Job Framework and the Sandbox  { data-toc-label="The Job Framework & the Sandbox" }

The [lava job framework](#the-lava-job-framework) uses standard AWS tools and
hence works fine with the sandbox. The framework can deploy jobs, payloads etc
to the sandbox, just as it does to AWS.

!!! info
    By default, the sandbox realm is `sandbox` and the worker name is `dev`.
    These can be changed, if desired.

Simply set the AWS profile and use the framework in the normal way:

```bash
export AWS_PROFILE=sandbox
# Assuming we a have "config/sandbox.yaml" in our framework project
# with the realm set to "sandbox".
make install env=sandbox
```

### S3 Events

The `lava-sandbox-realm` environment comes with an S3 bucket pre-configured to
dispatch a lava job when objects are created.

Objects created under the `s3://events/sandbox/` prefix will trigger a demo job
that logs the job specification, which includes the bucket and object name in
the job globals.

!!! note
    The `sandbox` prefix is based on the name of the realm. Modify it
    appropriately if the realm name is changed.

It's relatively straightforward to adapt or extend this for your own purposes.
See the CloudFormation template at `s3://cfn/extra-infra.cfn.json` in the
sandbox for inspiration.

See [Dispatching Jobs from S3 Events](#dispatching-jobs-from-s3-events) for more
information.

### Configuring the Sandbox

The sandbox requires no configuration to work out of the box. There are a few
parameters that can be fiddled with, if you must.

Create a `.env` file in the same directory as the Docker Compose file. Use the
following as a template.  Default values are shown.

```bash
# ------------------------------------------------------------------------------
# General configuration

LAVA_REALM=sandbox
LAVA_WORKER=dev
LAVA_VERSION=latest

# ------------------------------------------------------------------------------
# (Faux) AWS console container configuration.

# AWS console server port. Port 8080 can be crowded with other local services
# on a dev machine so we steer clear of it. Good old 8086. Happy days.
LAVA_SBX_CONSOLE_PORT=8086
# You can add "iam" and "kms" to this list if you wish, but they don't show
# anything of genuine interest and the more services, the slower the scan.
# The other one to contemplate is "secretsmanager".
LAVA_SBX_CONSOLE_SERVICES=s3,dynamodb,sns,sqs,lambda,logs,cloudformation,ssm,events

# ------------------------------------------------------------------------------
# Worker container configuration

# Emit a heartbeat log message every this many seconds. A value of 0 disables
# heartbeats. If specified, a minimum of 30 seconds is imposed.
LAVA_SBX_WORKER_HEARTBEAT=0

# Either "base" or "full". The latter includes additional components required to
# use CLI based connectors.
LAVA_SBX_WORKER_IMAGE_TYPE=base

# Emit messages of a given severity level or above. The standard logging level
# names are available but "debug" and "info" are most useful.
LAVA_SBX_WORKER_LOG_LEVEL=info

# If set to a non-empty value, run the worker in developer mode. This is passed
# through to the job hamdlers. It's up to them to decide what they do with this.
# Some handlers will print stuff to stdout rather than sending it to S3.
LAVA_SBX_WORKER_DEV_MODE=
```

### Loading Data

Data can be loaded into the sandbox, much as it would be loaded into a
conventional AWS environment using tools such as the AWS CLI, Python boto3 etc.
The sandbox can also pre-load user data for the following services on startup:

*   S3
*   DynamoDB
*   SSM parameter store.

Data should be placed in a `data` directory in the same base directory as the
[Docker Compose][DockerCompose] file, structured like so:

```plain
.
├── .env
│
├── data
│   ├── dynamodb
│   │   ├── table-1
│   │   │   ├── item-1.yaml
│   │   │   └── item-2.yaml
│   │   └── table-2
│   │       ├── item-3.yaml
│   │       └── item-3.yaml
│   ├── s3
│   │   └── my-bucket
│   │       └── my-data-file
│   ├── ssh
│   │   ├── my-ssh-key
│   │   └── my-ssh-key.pub
│   └── ssm
│       └── my-params.yaml
│
└── docker-compose.yaml
```

!!! tip
    Use the [Docker Compose][DockerCompose] `--project-directory` and `-f` /
    `--file` options to locate the data directory and Compose file elsewhere.

#### DynamoDB Data

The simplest and best way to load DynamoDB data is using the standard deployment
mechanisms of the [lava job framework](#the-lava-job-framework), pointed at the
sandbox.

However, data can also be pre-loaded into the sandbox by placing individual
table entries as YAML files in `data/dynamodb/<TABLE-NAME>/`. Table directories
are searched recursively. The format is normal YAML (not DynamoDB YAML).

The file name will have `${LAVA_REALM}` replaced with the lava realm name. So,
to load an entry to the [jobs](#the-jobs-table) table, place the YAML content
in the `data/dynamodb/lava.${LAVA_REALM}.jobs` directory.

References to `LAVA_REALM` and `LAVA_WORKER` in the data file will be
substituted using basic shell variable substitution syntax prior to loading.

For example, this is the content of `data/dynamodb/lava.realms/realm.yaml` used
to create the realms table entry on startup:


```yaml
config:
  CW_METRICS_PERIOD: 1m
  CW_METRICS_WORKER: false
  CW_METRICS_JOB: false
  STDERR_SIZE: -1024
  PAYLOAD_DOWNLOADER: v2
  SES_FROM: lava@sandbox.localhost
  SES_REGION: us-east-1
realm: '${LAVA_REALM}'
s3_key: alias/aws/s3
s3_payloads: 's3://lava/payloads'
s3_temp: 's3://lava/tmp'
x-workers:
  '${LAVA_WORKER}':
    threads: 3
    version: '${LAVA_VERSION}'
    workers: '${LAVA_WORKER}'
```

#### S3 Data

Files under `data/s3` will be replicated to S3 in the sandbox on startup.
The file name structure is `data/s3/<BUCKET>/<KEY>`. Buckets will be created, as
required.

#### SSH Keys

Some lava connectors require SSH keys to be stored as SSM parameters. Files
under `data/ssh` are assumed to contain SSH keys that will be loaded to the SSM
parameter store.

Files with a `.pub` suffix are assumed to contain public keys and are loaded as
`String` parameters with names in the form
`/lava/${LAVA_REALM}/ssh/<STEM>/public`, where `<STEM>` is the basename of the
file with the `.pub` suffix removed.

Files without a `.pub` suffix are assumed to contain secret keys and are loaded
as `SecureString` parameters with names in the form
`/lava/${LAVA_REALM}/ssh/<STEM>/secret`, where `<STEM>` is the basename of the
file.

#### SSM Parameters

The [lava job framework](#the-lava-job-framework) does not natively support
creating SSM parameters so the sandbox data loader is a good way to create
these.

YAML files under `data/ssm` (recursively) can contain one or more SSM parameter
specifications that will be automatically loaded when the sandbox starts.

The format is like so:

```yaml
Parameters:
  - Name: db/username
    Description: Database user name
    Type: String
    Value: lava
    Tags:
      - Key: MyTag
        Value: A tag value

  - Name: db/password
    Description: Database password
    Type: SecureString
    Value: ${DB_PASSWORD}
    KeyId: alias/lava-${LAVA_REALM}-sys

  - Name: random-string
    Description: Some random string 24 character string, good for passwords etc.
    Type: SecureString
    Value: ${SSMP_RAND_0}
    KeyId: alias/lava-${LAVA_REALM}-sys

```

The `Parameters` element is a list of objects, each of which specifies one SSM
parameter. Each parameter specification contains keys corresponding to the
parameters of the boto3 SSM client's [put_parameter][Boto3PutParameter]
operation.

The `Name`, `Description`, `Value`, `KeyId` and `Tags` support basic shell-style
substitution of the following:

*   Values specified in the `.env` file
    (see [Configuring the Sandbox](#configuring-the-sandbox))

*   `LAVA_REALM`, `LAVA_WORKER`

*   `AWS_REGION` / `AWS_DEFAULT_REGION`

*   `SSMP_RAND24_0` ... `SSMP_RAND24_9` : Random 24 character strings, using the
    base 64 charset, for things such as passwords when you need a value but
    don't care what it is.

Parameters with relative names (i.e. not starting with `/`) will have
`/lava/${LAVA_REALM}/` prepended to the name. This is the path prefix where
realm related SSM parameters would be stored in a standard lava environment.

For parameters of type `SecureString`, the `Value` *must* be nothing but a
variable substitution, as shown in the example above. Attempts to add any
literal content will result in an error. This reduces the risk of putting
unprotected secrets in a Git repo.

!!! important
    Make sure to include `.env` in `.gitignore`.

### Extending the Sandbox

The sandbox is essentially a pruned version of the docker based infrastructure
used to test lava itself. The latter also includes multiple database engines
(Postgres, Oracle, MySQL and Microsoft SQL Server) and emulators for, Slack
([Vercel emulate][VercelEmulate]) and Samba. It would be relatively
straightforward to extend the sandbox to include some of these additional
services.
