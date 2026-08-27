# Lava Testing

## Local Test Environment

Lava testing uses a suite of container based services to provide, or in some
cases emulate, infrastructure components.

Containerised versions of the following services are provided:

*   PostgreSQL
*   MySQL
*   Microsoft SQL Server
*   Oracle
*   Samba (SMB)
*   Docker registry via [JinDr](https://github.com/jin-gizmo/jindr)
*   AWS emulation via [Ministack](https://ministack.org) [^1]
*   Slack emulation via [Vercel Labs emulate](https://github.com/vercel-labs/emulate) [^2]
*   SMTP mail server emulation via [Mailpit](https://mailpit.axllent.org) [^3].

[^1]:   [Ministack](https://ministack.org) is a great and free (!) alternative to
        [LocalStack](https://www.localstack.cloud) since the latter decided to
        put most of it behind a paywall. 'Nuff said.
        [Kumo](https://github.com/sivchari/kumo) is also worth a look.

[^2]:   [Vercel Labs emulate](https://github.com/vercel-labs/emulate) is a great
        test tool that can emulate a bunch of services, one of which happens to
        be Slack. It's still a bit green in parts and the doco has a way to go
        but kudos and thanks to the Vercel Labs team for making it available. 
        Hope you keep adding to it.

[^3]:   [Mailpit](https://mailpit.axllent.org) is awesome!

The service containers are coordinated via Docker Compose. The configuration for
the services is in the `test/services` directory.

Some one-off configuration is required before starting the test environment.
See [Connecting to the Local Service Containers](#connecting-to-the-local-service-containers)
and [Credentials](#credentials) below.

The local test environment runs versions of the lava AWS Lambda functions in
Ministack. The Lambda code bundles must be built *before* starting the test
environment. The tests also require the Amazon Linux 2023 based lava docker
images. Do the following from the root of the repo:

```bash
# The Lambda code builds is done within a builder docker image.
# This builder image needs to be made first.
make builder runtime=amzn2023-py3.13

# Now we can build the Lambda function bundles.
make lambda

# Build the Amazon 2023 based lava images.
make --directory=docker build os=amzn2023
```

Once the initial build and configuration is done, start the test environment by
running the following command from either the repo root directory or the `test`
directory:

```bash
make start
# ... or ...
make up
```

To shutdown the test infrastructure:

```bash
make stop
# ... or ...
make down
```

The containers are used by some of the unit tests as well as by many of the test
jobs in the `test/jobs` directory.

## Refreshing Test Images

By default, test images are built as required by the `make start` process but
existing images are not refreshed, even if the base image has changed. Mostly,
this is fine and exactly what you want to happen.

Occasionally, it is necessary to update the test image because of changes in
the base image. Ministack, in particular, has frequent (almost daily) updates.

To force the test images to be refreshed:

```bash
make refresh
```

## Connecting to the Local Service Containers

The docker compose process described above will create a suite of local services
(e.g. database engines, SMB server) all connected to a common docker network.

> [!IMPORTANT]
>
> While all the services present on `localhost` from the host, the tests and
> some of the test infrastructure absolutely requires them to be addressable
> with hostname that matches the name of the container. The `/etc/hosts` entries
> described below are **essential**.

These are available at the following endpoints.

| Service        | Port(s)     | Host                |
| -------------- | ----------- | ------------------- |
| Mail           | 1025 / 8025 | lava-test-mail      |
| AWS emulator   | 4566        | lava-test-ministack |
| SQL Server     | 1433        | lava-test-mssql     |
| MySQL          | 3306        | lava-test-mysql     |
| Oracle Server  | 1521 / 2484 | lava-test-oracle    |
| PostgreSQL     | 5432        | lava-test-postgres  |
| Slack emulator | 4000        | lava-test-slack     |
| SMB Server     | 139 / 445   | lava-test-smb       |

In order for the same lava connectors to be used to access these, both from the
host and from within another container on the *same docker network*, the
following entries **must** be added to `/etc/hosts` on the host.

```text
127.0.0.1   lava-test-mail
127.0.0.1   lava-test-ministack
127.0.0.1   lava-test-mssql
127.0.0.1   lava-test-mysql
127.0.0.1   lava-test-oracle
127.0.0.1   lava-test-postgres
127.0.0.1   lava-test-slack
127.0.0.1   lava-test-smb
```

> The docker daemon needs to be allowed to map privileged ports to start the SMB
> server on ports 139 / 445. There is a special setting for this on docker
> desktop. You can try to map to higher ports but the smbprotocol implementation
> doesn't work properly.

### AWS Emulation with Ministack

For ministack access, the following entry should be placed in `~/.aws/config`

```ini
# Ministack
[profile mini]
region = us-east-1
endpoint_url = http://localhost:4566

# Ministack access from inside another container.
[profile minic]
region = us-east-1
endpoint_url = http://host.docker.internal:4566
```

This needs to go in `~/.aws/credentials`:

```ini
[mini]
aws_access_key_id = test
aws_secret_access_key = test

[minic]
aws_access_key_id = test
aws_secret_access_key = test
```

### Slack Emulation

The Slack emulator is [Vercel Labs emulate](https://github.com/vercel-labs/emulate).
In addition to webhook emulation (among other things), it also provides a simple
GUI at http://localhost:4000.

> [!IMPORTANT]
> [Vercel Labs emulate](https://github.com/vercel-labs/emulate) is an NPM
> package. Some corporate environments (rightly) block access to the public
> registry in favour of a curated registry via products such as Nexus. To get
> around this set the `NPM_CONFIG_REGISTRY` environment variable to the point to
> the alternate registry. This value is passed into the docker build process.

### SMTP Emulation

The SMTP emulator is [Mailpit](https://mailpit.axllent.org). It also provides a
nice little GUI at http://localhost:8025.

### Credentials

Credentials for the local services must be contained in `test/.env`. These must
match the credentials stored in the lava connectors deployed with the test jobs.
As `.env` files are not in the repo, this will need to be created manually. It
needs to contain the following:

```bash
# Used by the docker compose file

# Note: Some DBs don't let you control the admin user name.
# e.g. MySQL uses root and MsSQL uses sa.
DB_ADMIN_USER=master
DB_ADMIN_PASSWORD=...

SMB_USER=lava
SMB_PASSWORD=...

# Non admin user stuff. Must match the lava connectors being used.
DB_LAVA_USER=lava
DB_LAVA_PASSWORD=...

# This is not really secret given its a fixed value provided by the vercel
# emulator but this is a reasonable place for it.
SLACK_WEBHOOK=http://localhost:4000/services/T000000001/B000000001/X00000000

# Mail server stuff
SMTP_USER=lava
SMTP_PASSWORD=...
```

## ODBC Setup

See https://github.com/mkleehammer/pyodbc/wiki/Connecting-to-SQL-Server-from-Mac-OSX

Connecting to SQL Server requires ODBC and the FreeTDS driver. You can install
both of these with the platform package manager (e.g. yum/dnf, Homebrew etc).

The `odbcinst.ini` file then needs to be configured to point to the FreeTDS
driver. To find the correct location for `odbcinst.ini` run `odbcinst -j`.
You may need to hunt around for the location of the FreeTDS driver library.

On a Mac, this will look something like this:

```ini
[FreeTDS]
Description=Free TDS ODBC driver
Driver=/opt/homebrew/lib/libtdsodbc.so
Setup=/opt/homebrew/lib/libtdsodbc.so
UsageCount=1
```

Don't worry about `freetds.conf` or `odbc.ini`. They're not used.

## Test Jobs

Quite a few a test lava jobs are provided in the `test/jobs` environment. This
is structured as a standard lava job framework project. Some of the jobs /
connectors require a real AWS environment, particularly for AWS specific
services like Redshift and RDS Aurora. However, many of the jobs are setup to
run against the local test container environment.

To deploy the test jobs to the test environment (which must be running):

```bash
# Make sure our AWS API calls are pointed at our local AWS emulator.
export AWS_PROFILE=mini

# Build the test jobs and load all the artefacts into ministack
# (Except docker payloads which go into a local registry)
make load
```

## Running Tests

To run the tests:

```bash
make test

# or to get a coverage report in dist/test/htmlcov/
make coverage
```

## And now a word from our sponsor ...

Question: Are these unit tests, system tests or integration tests.

Answer: Yes. No. Don't care. They test stuff.

> Unit testing == the process of getting your mocks to work.
