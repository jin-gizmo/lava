## Deploying Lava Components

The lava code bundles can be deployed in any way that suits the target
environment. However ...

The mechanism that is supported by the lava distribution is to place them into
AWS S3 where they can be found, either by the supplied realm CloudFormation
templates in the case of the lambda functions, or the included deployment script
and EC2 instance boot scripts in the case of the worker / dispatcher bundle.

!!! note
    Note that the supplied [CloudFormation template for a lava worker](#) is
    dependent on the [lava EC2 AMI](#the-lava-ec2-ami) because of the unusual way
    it uses instance user data to run boot scripts to deploy the worker.
    Sorry about that. It's a legacy thing but it works.

### Lava Component Layout in S3

See also: [Deploying the Lava Components to S3](#deploying-the-lava-components-to-s3).

The components must be installed in AWS S3 in a layout like this:

```bare
s3://<s3CodeBucket>/<s3CodePrefix>/
├── _ami_
│   └── oracle
│       ├── instantclient-basiclite-linux-arm64.zip
│       ├── instantclient-basiclite-linux-x64.zip
│       ├── instantclient-sqlplus-linux-arm64.zip
│       └── instantclient-sqlplus-linux-x64.zip
|
├── _boot_
│   ├── 10-secupdate.sh
│   ├── 50-lava.sh
│   └── 90-motd.sh
|
├── _dist_
│   ├── cfn
│   │   └── v8.1.0
│   │       ├── lava-common.cfn.json
│   │       ├── lava-realm.cfn.json
│   │       └── lava-worker.cfn.json
│   ├── lambda
│   │   ├── dispatch-8.1.0.zip
│   │   ├── metrics-8.1.0.zip
│   │   ├── s3trigger-8.1.0.zip
│   │   └── stop-8.1.0.zip
│   └── pkg
│       └── amzn2023
│           ├── lava-8.0.0-amzn2023-py3.11-x86_64.tar.bz2
│           ├── lava-8.1.0-amzn2023-py3.11-aarch64.tar.bz2
│           └── lava-8.1.0-amzn2023-py3.11-x86_64.tar.bz2
|
├── <REALM-1>
│   ├── <WORKER-1A>
│   │   ├── root.boot.sh
│   │   └── root.boot0.sh
│   └── <WORKER-1B>
│       ├── root.boot.sh
│       └── root.boot0.sh
|
└── <REALM-2>
    └── <WORKER-2A>
        ├── root.boot.sh
        └── root.boot0.sh
```

!!! info
    `s3CodeBucket` and `s3CodePrefix` are parameters in the
    [realm CloudFormation template](#the-lava-realm-cloudformation-template).


| Prefix | Description|
| ------ | -----------------------------|
| `_ami_` | Used by the build process for the [lava AMI](#the-lava-ec2-ami). It contains large packages that are baked into the lava AMI as it's quicker to get them from S3 rather than upload them to the build instance each time. It is not used in the worker boot process.|
| `_boot_` | These scripts are downloaded and run during the worker EC2 boot process. The critical one for the lava worker is `50-lava.sh` which downloads the worker code bundle from S3 and installs it. The source for these scripts is `misc/boot/` in the [lava repo](#the-lava-repo). |
| `_dist_` | Contains the lava distribution. Multiple lava versions can safely sit side by side in here.|
| `_dist_/cfn` | Contains the CloudFormation templates and associated auto-generated documentation. |
| `_dist_/lambda` | Contains the code bundles for the Lambda functions. Version selection is controlled by a parameter in the [realm CloudFormation template](#the-lava-realm-cloudformation-template). |
| `_dist_/pkg` | Contains the main lava worker code bundle organised by target O/S, architecture and Python version. Multiple versions are allowed. See also [Lava Version Selection](#lava-version-selection). |
| `<REALM>/<WORKER>` | Contains the worker EC2 instance primary boot scripts. While these scripts are installed on a per worker basis they should generally be identical across all accounts, realms and workers. It is possible to have a worker specific setup if required. Versions of these are provided in the `misc` directory of the [lava repo](#the-lava-repo). The supplied versions basically just download and run the scripts in the `_boot_` area. |

### Deploying the Lava Components to S3 { data-toc-label="Deploying to S3" }

While not mandatory, lava assumes that most environments will need to deploy all
of the built assets to AWS S3 where they can be accessed as required. This
includes the worker and dispatcher code and lambda functions. This can be
tedious to do manually so a basic deployment script is provided in
`etc/deploy.sh`.

It will read a YAML configuration file that tells it what to deploy and where to
deploy it. It supports deployment of the following lava components (depending
on the contents of the configuration file):

*   S3 artefacts in the structure illustrated [above](#lava-component-layout-in-s3).

    *   lava code bundles (`_dist_/pkg/`)
    *   boot scriptlets (`_boot_/`)
    *   the lava Lambda functions (`_dist_/lambda/`)

*   The lava job framework bundle to S3

Usage is:

```bare
Usage: deploy.sh -e environment [-f deploy.yaml ] [-d] [-h] [-n] [component ...]

Args:
    -e environment      Target environment. The deploy.yaml file must contain a
                        key for this.

    -f deploy.yaml      Specify a YAML file containing S3 target locations. If
                        not specified, the default is deploy.yaml in the current
                        directory.

    -d                  Dry-run.

    -h                  Print help and exit.

    -l                  List deployable components and exit.

    -n                  Same as -d like make(1).

    -v                  Deploy the specified lava version. If not specified,
                        the latest version is deployed (currently 8.1.0).


    component           Only deploy the named components. If not specified, all
                        available components for which there is a a deployment
                        on on the specification file will be deployed.
```

It should be run from the base directory of the repo. A sample deployment
configuration file is provided as `deploy/sample.yaml`. Format
information is contained in that file. The script is rather basic but will
attempt to avoid copying files that aren't required in a given environment or
that don't need updating.

A configuration file may contain specifications for multiple environments. These
are selected by the mandatory `-e environment` of `etc/deploy.sh`. To avoid
accidents, the configuration for an environment must specify the target AWS
account ID.

!!! info
    The configuration file also contains parameters used to
    [build the lava AMI](#building-the-lava-ami). These are ignored by `etc/config.sh`.

To list the possible deployable components run `etc/deploy.sh -l`. This will
produce something like this:

```bare
❯ etc/deploy.sh -l
ami        Components required to be in S3 to build the AMI (not the AMI itself).
boot       Lava worker boot scriptlets (not root.boot*).
framework  Lava job framework.
lambda     Lambda function code bundles.
pkg        Main lava code package.
```

A configuration file may restrict this further by not including configuration
information for some of these targets.

To deploy everything that is configured for a given environment:

```bash
# First do a dry run to see what would be deployed ...
etc/deploy.sh -n -f deploy/my-config.yaml -e dev

# Now deploy for real ...
etc/deploy.sh -f deploy/my-config.yaml -e dev
```

Just deploy a specific component:

```bash
# Deploy docs only
etc/deploy.sh -f deploy/my-config.yaml -e dev doc
```

### Lava Version Selection

#### Lambda Functions

The `lambdaVersion` parameter in the [realm CloudFormation
template](#the-lava-realm-cloudformation-template) specifies the version to use
for the lambda functions. To change versions, update the realm stack.

The stack will look for the lambda code in
`s3://<s3CodeBucket>/<s3CodePrefix>/_dist_/lambda/` where `s3CodeBucket`
and `s3CodePrefix` are also stack parameters.

#### Lava Workers

The supplied `misc/boot/50-lava.sh` script is deployed into
`s3://<s3CodeBucket>/<s3CodePrefix>/_boot_/` and runs when the EC2 worker
instance boots.

By default, the script will attempt to install the highest available version
that matches the instance O/S type, Python version and architecture. However, a
specific version can be selected by [adding worker configuration entries to the
realms table](#adding-worker-configuration-entries-to-the-realms-table).

The package selection sequence is this:

1.  If a version is
    [specified in the realms table](#adding-worker-configuration-entries-to-the-realms-table):
    1.  Look for a package with the new package naming style (i.e. version,
        O/S, architecture and Python must match). If one is found, use that.
    
    2.  Look for a package of the required version with the old naming
        style. If one is found, use that.
    
2.  If a version is not specified in the realms table:

    1.  Find the latest matching version using the new package naming
        style. If one is found, use that.

    2.  Find the latest version using the old package name style. If one
        is found, use that.

3.  Otherwise, give up and abort.

