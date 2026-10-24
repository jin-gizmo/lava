
## The Lava EC2 AMI

The lava worker utilises a suite of external capabilities on the host platform.
Examples include:

*   A stable and predictable Linux O/S
*   A compatible version of Python
*   Docker
*   The Postgres, MySQL and Oracle CLI binaries
*   The Oracle driver and SQL*Plus binary
*   UnixODBC and FreeTDS for accessing MSSQL databases
*   AWS RDS and Redshift trust certificates
*   AWS SSM agent for host maintenance
*   AWS CloudWatch logs agent
*   Some of the platform dependent Python packages (e.g. psutil).

... and, of course, ...

*   The lava worker code bundle.

The lava EC2 AMI incorporates all of the required components, except for the
lava code bundle itself, which is loaded from S3 at boot time.
This makes it easier to roll the
deployed lava version forward/backward just by changing an entry in the
[realms table](#the-realms-table) and rebooting.

The lava AMI is based on Amazon Linux 2023. X86 and Graviton EC2 instances are
supported.

### Lava AMI Names

Lava AMI names look like so:

```bare
lava-8.1.0-amzn2023-py3.11-arm64-2025-07-02T08-43-48Z
     --+-- ---+---- --+--- --+-- ----------+---------
       |      |       |      |             |
       |     O/S      | Architecture       |
       |      |       |                    |
     lava     |    Python                Build
    Version   |    Version               Date
              |       |
              +---+---+
                  |
               Runtime
```

!!! note
    With AMI names, the architecture for ARM is always `arm64`, never `aarch64`.
    Lava worker code bundles for ARM can have either `arm64` or `aarch64`,
    depending on how the target operating system identifies its platform. You
    say tomato ... (Google it Grasshopper).

### Lava AMI Architecture

The lava AMI can be built for different CPU architectures. Typically this is one
of `x86_64` or `arm64`.

This can affect lava job payloads for [pkg](#job-type-pkg) jobs. If the payload
contains binary components, they may have a dependency on a particular machine
architecture.

### Lava AMI Versions

Lava AMI versions are derived from the version number of a given lava release
(e.g. v8.1.0). While there is generally not a hard binding between the lava
worker version and the AMI version, its best to keep them as close to in-sync
as possible.

### Python Versions in the Lava AMI

The lava AMI can be built with different Python versions. This can affect lava
job payloads for [pkg](#job-type-pkg) jobs. If the payload contains Python
components, they may have a dependency on a particular version of Python.

The Python version for a lava AMI is also indicated in the `PYTHON_VERSION` tag
on the AMI, and also in the AMI name.

!!! tip
    If possible, use the `PYTHON_VERSION` tag in preference to the AMI name if
    checking for Python version in case of future name structure changes.

### Building the Lava AMI

The lava AMI is built using [packer](https://www.packer.io). Most of the
components for the build are in the `ami` directory in the lava repo. Some
components (e.g. large 3rd party code bundles like the Oracle drivers) must be
loaded to a specified location in S3 prior to the build. The build process will
do this for you. This is done to speed up the build process as it avoids the
need to transfer these to the build instance at build time.

The build process leaves the following artefacts on the AMI in `~ec2-user/packer`:

*   The build components

*   The detailed log from the build.

The packer executable is also installed.

In theory, an instance based on the lava AMI can be used to rebuild the AMI
itself.

The essence of the process to build the AMI is:

```bash
# Make sure the lava virtualenv is activated first!

# From the top of the lava source repo...
cd ami

# Get some help, just in case...
make help

# Build the AMI...
make ami param=value ...
```

This will first sync the required S3 based components from the local
filesystem to S3 and then initiate the [packer](https://www.packer.io) build. A
number of tags are added to the resultant image to record things such as the
corresponding lava version and the installed Python version.

The trick to the process is getting the build parameters right for the target
environment. These are either specified on the **make** command line with the
`param=value` arguments (the [hard way](#the-hard-way-specifying-build-parameters-manually))
or obtained from a configuration file
(the [easy way](#the-easy-way-reading-build-parameters-from-a-configuration-file)).

|Parameter|Required|Description|
|--|--|-------------|
|ami_id|No|ID of the base AMI. If not specified, the `ami_ref` is read from `ami-build.yaml`, which is then used to lookup the AMI ID. Don't mess with this unless you really know what you're doing.|
|ami_ref|No|The `ami_ref` is the tail of an AWS SSM parameter name containing the ID of the base AMI. AWS provides a bunch of these parameters to simplify finding common AMIs. e.g. `al2023-ami-kernel-default-x86_64`. See https://docs.aws.amazon.com/linux/al2023/ug/ec2.html. If not specified, the `os` is looked up in `ami-build.yaml` to obtain the value.|
|arch|No|The CPU architecture. This must be one of `x86_64` (default) or `arm64`.|
|config|No|Name of a YAML configuration file (in lava deploy format) containing values for any or all of the required parameters. A configuration file can contain separate configurations for different environments (e.g. dev, prod etc.). If specified, the `env` parameter is also required. The AMI configuration parameters are specified under the `<ENV> -> ami` key. A sample configuration file can be found in `deploy/sample.yaml`.|
|env|No|The environment identifier within a specified configuration file.|
|os|Yes|The O/S type of the AMI to be built. Allowed values are specified in `ami-build.yaml` and must correspond to a builder in the `os` directory. Currently supported values are `amzn2` (Amazon Linux 2) and `amzn2023` (Amazon Linux 2023).|
|instance_type|No|The AWS EC2 build instance type. This must match the CPU architecture specified by `arch`. e.g. If the `arch` is `arm64`, a Graviton build instance must be selected. If not specified, the value is read from `ami-build.yaml`.|
|ip|Yes|IP address type for the packer build instance. Either `public` or `private`|
|python_version|Yes|The Python version to build from source for the AMI (e.g. `3.11.12`).|
|s3bucket|Yes|Name of the S3 bucket containing extra build resources (e.g. Oracle client binaries).|
|s3prefix|Yes|The S3 prefix containing extra build resources (e.g. Oracle client binaries).|
|sg|Yes|Security group ID (or a comma separated list of IDs) for the packer build instance.|
|subnet|Yes|Subnet ID for the packer build instance.|
|tz|Yes|Timezone to set in instances created from the lava AMI (e.g. `Australia/Sydney`)|


#### The Hard Way - Specifying Build Parameters Manually

The required configuration parameters can all be specified as part of the **make**
command line, like so:

```bash
make ami \
    ami_id="ami-0043df2e553ad12b6" \
    ip="public" \
    python_version="3.11.12" \
    s3bucket="my-artefact-bucket" \
    s3prefix="lava/ami/" \
    sg="sg-004d25956a3bf5bd4" \
    subnet="subnet-f6b6d681" \
    tz="Australia/Sydney"
```

This gets old very quickly when building for multiple environments.


#### The Easy Way - Reading Build Parameters from a Configuration File

All of the mandatory build parameters can be placed in a YAML configuration file
(let's call it `config.yaml`) formatted like so:

```yaml
# This is the config for the "dev" environment. The file can contain
# multiple environments.
dev:
  # The underscore key is for general config
  _:
    # If other S3 location keys don't start with s3:// this base is used.
    # Don't add trailing / here.
    s3base: my-bucket/a/prefix

  # Parameters for packer when building the lava ami.
  ami:
    # Location of additional resources for building the lava AMI.
    s3: lava/ami/
    # Public or private IP address for the build
    ip: public
    # Build instance subnet
    subnet: subnet-f6b6d681
    # Security groups -- this must be a comma separated list (no spaces)
    sg: sg-004d25956a3bf5bd4
    # Timezone set on instances created from the AMI.
    tz: Australia/Sydney
    # Python version to build from source
    python:
      version: "3.11.12"
```

The configuration file is in lava standard deploy format and may also contain
other parameters for deploying the lava code bundles to S3 etc. A sample version
is provided in `deploy/sample.yaml`.

The AMI build process then becomes:

```bash
make ami config=config.yaml env=dev
```

It is still possible to override individual parameters like so:

```bash
make ami config=config.yaml env=dev python_version=3.11.11
```

### User Data for the Lava AMI

When a lava AMI instance boots, the normal Linux boot process will eventually
get around to running `/etc/rc.local`. At the end of this, a lava AMI specific
process runs all of the scripts in the directory `/usr/local/etc/rc.d`. A number
of these scripts examine the EC2 instance user data, expecting to find a JSON
formatted object which they search for keys that provide configuration
instructions.

The following keys are currently supported in the user data JSON. All of the
top level keys are optional. If not present, the relevant script will take no
action.

| Key | Sub-key | Description |
| --- | --- | ------------------------------- |
| crontab | `<USER_NAME>` | A dictionary of Linux instance user names. The value for each user name is the name of an S3 object containing the crontab for that user. |
| shell | - | A string (or list of strings) containing a command (or list of commands) to run. This runs after all the other startup scripts have run. This is used by the lava [worker CloudFormation template](#the-lava-worker-cloudformation-template) to invoke the lava installer to download, install and run the lava worker code on boot.|
|shell0| - | Same as the `shell` key except this runs before any of the other scripts. |
|swap|size| If present and non-zero, swapping is enabled. The value is the swap file size in Gibibytes (1024 * 1024 * 1024 bytes). The swap file is on the root volume so there must be adequate space to hold it. More information on [swap space](https://www.linux.com/news/all-about-linux-swap-space/) and [swap file size selection](https://help.ubuntu.com/community/SwapFaq#How_much_swap_do_I_need.3F).|
|swap|file| Name of the swap file. It must be on the root volume. The default is `/swapfile`.|


For example, the following user-data will cause a lava AMI based instance to:

*   Install a crontab file for users `ec2-user` and `root`.

*   Enable swapping with swap file of 2GiB.

*   Run a couple of shell commands.

```json
{
  "swap": {
    "size": 2,
    "file": "/swap_till_you_drop"
  },
  "crontab": {
    "ec2-user": "s3://mybucket/ec2config/latest/ec2-user.cron",
    "root": "s3://mybucket/ec2config/latest/root.cron"
  },
  "shell": [
    "echo Hello world",
    "echo Resistance is futile > /tmp/borg"
  ]
}
```

### Configuring a Lava Worker EC2 Instance to Use a Lava AMI { data-toc-label="Configuring a Worker EC2 to Use a Lava AMI" }

The AMI used by an EC2 based lava worker is specified as a parameter in the
[worker CloudFormation template](#the-lava-worker-cloudformation-template).

The template creates the necessary EC2 launch template and auto scaler and
also ensures the instance user data is correctly constructed to install and
start the lava worker(s) on boot.

To select or change the AMI, simply update the relevant worker CloudFormation
stack. While this can be done from the AWS console, it is more convenient to use
the [lava-ami](#lava-ami-utility) utility which displays the available, lava
compatible, AMIs and the AMI specified in each lava worker CloudFormation stack.
It also provides an update mode that allows a (more or less) interactive process
to select and apply a different AMI to one or more lava worker stacks.
