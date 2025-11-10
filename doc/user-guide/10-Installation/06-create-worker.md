## Creating a Lava Worker

!!! info
    It is important to read *all* of this section before starting to create a
    worker.

Each realm can have an arbitrary number of workers of different capabilities to
run jobs.

Workers can run on Linux / macOS with Python 3.9+ installed.

There are different ways to run the lava worker.
The worker can be run interactively or as a multi-threaded daemon. It is
possible to run multiple workers on a single instance. 

The first worker created will typically also serve as a dispatcher for scheduled
jobs. Dispatcher workers must
each run in their own operating system account to ensure crontab separation.

Creating a worker involves two distinct aspects:

1.  Use the
    [lava worker CloudFormation template](#the-lava-worker-cloudformation-template)
    to create the AWS resources required by the worker (e.g. SQS queue, EC2
    components etc).

2.  Create a compute environment to run the actual lava worker. The most common
    options for doing this are:
    1. [Desktop workers](#desktop-lava-workers)
    2. [Docker lava workers](#docker-based-lava-workers)
    3. [EC2 based workers](#ec2-based-lava-workers)
    4. [Parasitic workers](#parasitic-lava-workers).

### The Lava Worker CloudFormation Template { data-toc-label="Worker CFN Template" }

!!! note
    Pre-built versions of the CloudFormation templates are provided as part of
    a [release on GitHub](https://github.com/jin-gizmo/lava/releases).

The [worker CloudFormation template](#lava-workercfnjson) is located in the
[lava repo](#the-lava-repo).
See [Building the CloudFormation Templates](#building-the-cloudformation-templates).

The lava worker CloudFormation template is a single entity but it contains
parameters (and associated resources) in three broad groups:

1.  [Core worker parameters](#core-worker-parameters): These are necessary for
    any lava worker, unrelated to where, or whether, the worker process is
    running. e.g. the worker SQS queue, queue depth alarm etc.

2.  [EC2 worker parameters](#ec2-worker-parameters): These parameters are
    associated with the operating resources needed for an AWS EC2 instance
    running the worker process. e.g. launch configuration, auto scaling group,
    IAM role for the worker etc.

3.  [EC2 instance selection parameters](#ec2-instance-selection-parameters):
    These parameters control the way in which the EC2 instance type is chosen.

These are all parameters of the same template but are described separately below
for clarity.

#### Core Worker Parameters

The core worker parameters and associated resources are necessary for a lava
worker to exist, whether or not there is an actual worker process anywhere or
where it is located.

In broad terms, these relate to resources that are not EC2 related.

| Parameter                        | Description                                                  |
| -------------------------------- | ------------------------------------------------------------ |
| Version                          | This is a **read-only** informational parameter that indicates the lava version associated with the template. |
| alarmTopic                       | Name of an SNS topic for alarms. The topic must already exist. |
| autoscalingControlledTermination | If `ENABLED`, auto scaling controlled termination on worker nodes is enabled. Best not to fiddle with this. |
| maxAllowedQueueDepth             | Create a CloudWatch alarm if queue depth exceeds this value. Set to 0 for no alarm. |
| messageRetentionPeriod           | Message retention period on the worker SQS queue in seconds. Default 1 day. Must be >= 1800 (30 minutes). |
| queueDepthMinutes                | Minutes worker SQS queue depth exceeds `maxAllowedQueueDepth` before alarming. |
| realm                            | Name of the realm.                                           |
| realmLambdasDeployed             | Are the realm lambda functions deployed? This should almost always be set to `Yes`. |
| visibilityTimeout                | Visibility timeout on the worker queue (seconds). Default 1 hour. |
| worker                           | Name of the worker.                                          |

#### EC2 Worker Parameters

These parameters control creation of resource required to run an EC2 based lava worker. They are triggered by setting the `createWorkerInstance` parameter to `Yes`.

| Parameter                  | Description                                                  |
| -------------------------- | ------------------------------------------------------------ |
| amiId                      | AWS EC2 Image ID for the worker EC2 instance. This should be the ID for a [lava AMI](#the-lava-ec2-ami). Can be left blank if `createWorkerInstance` is `No`. |
| autoscalingActionTopic     | Name of an SNS topic for reporting normal auto scaling activity. If required, the topic must already exist. |
| createHeartBeatAlarm       | If `Yes` a CloudWatch alarm will be created for a loss of heartbeat messages from a worker. Set to `No` for non-EC2 based workers. |
| createWorkerInstance   | If `Yes`, the required components for an EC2 based worker will be created. Set to `No` if the worker will be running on an existing compute environment (e.g. local machine or parasitic on an existing worker). |
| dockerVolumeSize           | If non-zero (GB) a dedicated EBS volume for docker will be added to an EC2 based worker. This is a good idea if the worker will be running docker jobs to isolate large storage needs for docker images. |
| keyPairName                | SSH key pair to assign to EC2 based instances. If left empty, no SSH key is assigned. |
| rootVolumeSize             | Size in GB of the root volume on an EC2 based instance. Set to 0 for the default value associated with the AMI. This would typically be increased if not creating a dedicated temporary volume or if swapping is enabled. See also `tmpVolumeSize` and `swapSize`. |
| secGroups                  | A list of (existing) EC2 security groups to attach to an EC2 based instance. |
| subnets                    | A list of (existing) VPC subnets in which EC2 based instances can be placed. |
| swapSize                   | Swap size in Gibibytes (0 = no swapping). This may require a bigger root volume. See `rootVolumeSize`. |
| tmpVolumeSize              | Size in GB of a dedicated EBS volume mounted on `/tmp` for EC2 based instances. Set to 0 to remove. If the worker is going to be processing disk I/O bound jobs, a larger tmp volume may help due to increased provisioned IOPS. |
| workerBacklogScalingTarget | Auto scaling worker backlog. Set to 0 to disable backlog scaling. See [Lava Worker Auto Scaling](#lava-worker-auto-scaling). |
| workerInstancesDesired     | The number of desired EC2 based instances. This is used by the auto scaling group. |
| workerInstancesMax         | The maximum number of EC2 based instances the auto scaling group will provision. |
| workerInstancesMin         | The minimum number of EC2 based instances the auto scaling group will provision. |
| workerPublicIp         | Assign a public IP to the worker.                            |

#### EC2 Instance Selection Parameters

The [EC2 Worker Parameters](#ec2-worker-parameters) described above specify
*how* to create an EC2 based lava worker but they do not specify what instance
type to use. This is done by the parameters specified below.

Two different methods of instance type selection are supported:

1.  **Explicit instance type provisioning**: This is triggered by setting the
    `workerInstanceType` parameter to a single EC2 instance type (e.g.
    `m3.large`).    

    The required instance type will be specified in the worker launch template.
    The advantage of this approach is that it is simple and direct. The
    disadvantage is that, if AWS has a capacity shortage for the specified
    instance type, the auto scaler may not be able to create a worker or fully
    satisfy the auto scaler's demands. The risk of this seems to increase for
    the larger instance types.

2.  **Capability based provisioning**: If `workerInstanceType` is not set, the
    other parameters are used to indicate the capabilities required of the
    worker instance.

    These parameters control the inclusion of a [mixed instances
    policy](https://docs.aws.amazon.com/autoscaling/ec2/APIReference/API_MixedInstancesPolicy.html)
    in the auto scaling group definition. No instance type information is
    included in the launch template.  This gives the auto scaler the
    ability to choose any instance type that meets the capability requirements.
    Lava workers don't much care about instance type. They mostly care about
    memory, CPU and storage.

    The advantage of this approach is increased resilience in the face of AWS EC2
    capacity shortages.

| Parameter              | Description                                                  |
| ---------------------- | ------------------------------------------------------------ |
| workerAllowedInstances | Comma separated list of allowed instance types (GLOBs allowed) for EC2 based workers using capability based provisioning. e.g. `*` Would allow any instance type. `m3.*,c3.*` would allow any M-series or C-series instance type that meets memory and CPU requirements. A value must be specified if `workerInstanceType` is not set. |
| workerBurstable        | Include burstable instance types (e.g. T-series) for EC2 based workers using capability based provisioning. |
| workerInstanceType     | If set to an AWS instance type, an EC2 based instance will use the specified type. If not set, capability provisioning will be used to select an EC2 instance type. |
| workerLocalStorage     | Controls inclusion of EC2 instance types with local storage when performing capability based provisioning. |
| workerMemoryMax        | Maximum memory in MiB (*not* MB) for EC2 instance types when performing capability based provisioning. Set to 0 to remove the upper limit. |
| workerMemoryMin        | Minimum memory in MiB (*not* MB) for EC2 instance types when performing capability based provisioning. |
| workerVCpuMax          | Maximum number of vCPUs for EC2 instance types when performing capability based provisioning. Set to 0 to remove the upper limit. |
| workerVCpuMin          | Minimum number of vCPUs for EC2 instance types when performing capability based provisioning. |

### Desktop Lava Workers

Once the [core worker components](#core-worker-parameters) are created for a
lava worker, it is straightforward to run the lava worker on a macOS or Linux
desktop, provided the user has the appropriate IAM permissions.

The setup will look something like this (not including installing non-lava
prerequisites):

```bash
# Create a virtual env to be safe
mkdir lavaworker
cd lavaworker
python3 -m venv venv
source venv/bin/activate

# Install
pip3 install jinlava

# Get help
lava-worker --help

# Run a lava worker interactively for development / debugging
lava-worker --realm <REALM> --worker <WORKER> --level debug --dev
```

### Docker Based Lava Workers

A straightforward way to run a lava worker on a local machine is to use one of
the pre-built lava images. This will include all of the non-lava prerequisites
and all of the lava utilities, include the lava worker.

```bash
# First, log in to ECR then ...
docker pull \
    "<ACCOUNT_NO>.dkr.ecr.ap-southeast-2.amazonaws.com/dist/lava/amzn2023/base"

# Run the container
docker run -it --rm \
    "<ACCOUNT_NO>.dkr.ecr.ap-southeast-2.amazonaws.com/dist/lava/amzn2023/base"

# Get help
lava-worker --help

# Setup AWS profile then ... 

# Run a lava worker interactively for development / debugging
lava-worker --realm <REALM> --worker <WORKER> --level debug --dev
```

### EC2 Based Lava Workers

!!! note
    This is the standard shared use and production configuration for a lava
    worker.

!!! info
    The following process assumes the [lava deployment
    artefacts](#building-lava-components) and the [lava EC2
    AMI](#the-lava-ec2-ami) have already been built and [deployed to
    S3](#deploying-lava-components). Ensure that matching Python versions and
    platform architectures are selected throughout for any given worker.

The preferred deployment configuration for a production or shared-use lava
worker is to use the [lava worker CloudFormation
template](#the-lava-worker-cloudformation-template) to create EC2 instances,
based on the [lava AMI](#the-lava-ec2-ami), running the lava worker code bundle.

The setup process is:

1.  [Deploy the Lava Components to S3](#deploying-the-lava-components-to-s3)
    if not already present. These will be read by the worker EC2 at boot time.

2.  [Install the worker boot scripts](#installing-the-worker-boot-scripts).
    These will be read by the worker EC2 at boot time.

3.  Add
   [worker configuration entries](#adding-worker-configuration-entries-to-the-realms-table)
   to the [realms table](#the-realms-table) to specify the run-time
   configuration of the worker.

4.  Build the [worker CloudFormation stack](#the-lava-worker-cloudformation-template)
    with these settings:

    *    `createWorkerInstance`=`Yes` 
    *    `workerInstancesDesired`=`0`
    *    `createHeartBeatAlarm`=`No`

    If the `createWorkerInstance` parameter is set to `Yes` when deploying the
    [lava worker CloudFormation template](#the-lava-worker-cloudformation-template),
    additional resources are created to host a lava worker on an EC2 instance
    (e.g. worker IAM role, launch template, auto scaling group etc). Setting
    `workerInstancesDesired` to `0` still creates these components but no
    active EC2 instances.

5.  Update the worker IAM role if required.

    The previous step will create the required EC2 resources for the worker  but
    not start an EC2 instance. It will also create an IAM role
    `lava-<REALM>-worker-<WORKER>` . This will contain the core permissions to
    allow a worker to function. It may be necessary to add other, environment
    specific policies to this before starting an actual EC2 instance.

6.  If the worker is going to be a dispatcher, create a [lavasched](#job-type-lavasched)
    job in the realm jobs table. The worker *jump-start* process will
    automatically build a crontab schedule when the EC2 instance boots.

7.  Update the [worker CloudFormation stack](#the-lava-worker-cloudformation-template)
    with these changes:

    *   `workerInstancesDesired`=`1`
    *   `createHeartBeatAlarm`=`Yes`

An EC2 instance will be created that can be accessed via SSM session manager. It
can take a few minutes for lava to install and start. The configuration is as
shown below:

![lava production deployment](img/deploy-config.svg)

The start up process for the worker is:

1.  The CloudFormation template configures the the worker auto scaling group to
    start one or more instances.

2.  The worker auto scaling group starts an EC2 instance using the
    [lava AMI](#the-lava-ec2-ami) as a base.

3.  The EC2 instance reads [boot scripts](#installing-the-worker-boot-scripts)
    from S3 and runs them.

4.  The boot scripts read
    [worker configuration](#adding-worker-configuration-entries-to-the-realms-table)
    from the realms table (lava version, how many daemons to run etc.)

5. The boot scripts read the lava code bundle from S3, install it, and configure 
    and start the lava worker daemons.

#### Adding Worker Configuration Entries to the Realms Table

By default, the EC2-based worker boot process will attempt to install the
highest available lava version that matches the host Python version and hardware
architecture. It will also start a single lava worker daemon.

The realms table entry can contain parameters under the `x-workers.<WORKER>`
key that modify the behaviour of this process as follows. Note that a `<WORKER>`
value of `_` in the realms table can provide defaults for all workers where
a worker specific value is not provided.


| Key | Type | Description |
| --- | ---- | ----------- |
| daemons | Integer | The number of worker daemons to run. The default is 1.|
| env | Map | A map of variables that will be placed in the worker's environment.|
| threads | Integer | Number of threads to run per worker daemon. |
| version | String | Lava version to install (e.g. 8.1.0). |
| workers | String | A space separated list of workers to run. This is used for [parasitic workers](#parasitic-lava-workers). |

```json
{
  "realm": "prod01",
  "x-workers": {
    "core": {
      "threads": 6,
      "version": "8.1.0"
    },
    "_": {
      "env": {
        "AWS_MAX_ATTEMPTS": 10,
        "AWS_METADATA_SERVICE_NUM_ATTEMPTS": 10,
        "AWS_RETRY_MODE": "adaptive",
        
      }
    }
  }
}
```

This will cause the instance to install lava version 8.1.0 on the machine and
start a worker `lava-prod01-core` running 6 threads. The worker will have the
three `AWS_*` environment variables set.

#### Installing the Worker Boot Scripts

The worker boot scripts, `root.boot0.sh` and `root.boot.sh` configure the EC2
instance and install lava. The user data in the launch template will tell an
instance created from a [lava AMI](#the-lava-ec2-ami) to run the boot scripts
when the worker instance boots. It will also provide the S3 location to obtain
the code.

The lava repository contains versions of these boot scripts in the `misc`
directory. They can be used as is or tailored as required.

These scripts must be placed in the same area of S3 as the lava code in
sub-prefixes specifying the realm and worker names as shown in
[Lava Component Layout in S3](#lava-component-layout-in-s3).

The supplied version of `root.boot.sh` basically just downloads and runs the
boot scripts from the `_boot_/` prefix in the
[S3 deployment area](#lava-component-layout-in-s3).

### Parasitic Lava Workers

It is possible for multiple lava workers to share a single EC2 instance. In this
case, exactly one of the workers will have an associated EC2 instance and the
other parasitic workers will hitch a ride on that.

The host worker is created first as described [above](#ec2-based-lava-workers).

This is the process to add a parasitic worker:

1.  Use the [lava worker CloudFormation template](#the-lava-worker-cloudformation-template)
    to create an additional worker with `createWorkerInstance`=`No`. 

2.  Update the realm entry in the [realms](#the-realms-table) table to configure
    the extra worker to run on the same host as the existing worker (see below).

3.  If the parasitic worker is going to be a dispatcher, create a
    [lavasched](#job-type-lavasched) job in the realm jobs table. The worker
    *jump-start* process will automatically build a crontab schedule when it the
    EC2 instance boots.

4.  Reboot or replace the EC2 instance. Both workers should now start on the one
    host.

The following example shows the changes in the [realms](#the-realms-table) table
to add a `core-bulk` worker to the primary `core` worker.

```json
{
  "realm": "prod01",
  "x-workers": {
    "core": {
      "threads": 6,
      "version": "8.1.0",
      "workers": "core core-bulk"
    },
    "core-bulk": {
      "daemons": 2,
      "threads": 8,
      "version": "8.1.0"
    },
    "_": {
      "env": {
        "AWS_MAX_ATTEMPTS": 10,
        "AWS_METADATA_SERVICE_NUM_ATTEMPTS": 10,
        "AWS_RETRY_MODE": "adaptive"
      }
    }
  }
}
```

Note the addition of `"workers": "core core-bulk"` entry in `workers -> core`.
This tells the worker boot script to run an extra worker.

The `"core-bulk": { ... }` section specifies the configuration of this extra
(parasitic) worker.

Points to note:

1.  The workers can, if required, run different versions of lava.
2.  The `"daemons": 2`element will start 2 workers named `lava-prod01-core-bulk`,
    each running 8 threads.
3.  One worker EC2 host cannot run workers belonging to different realms.

Its important to be aware of the following when running multiple worker daemons
with the same name on the same machine:

*   This configuration is experimental.
*   They will all service the same SQS job queue.
*   They will all emit heartbeat messages under the same name.
*   They will all produce worker CloudWatch metrics for the same metrics, if that
    configuration option is enabled. See [Worker Metrics](#worker-metrics).
