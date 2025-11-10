
# Lava Installation and Operation { x-nav="Installation & Operation" }

!!! info
    Lava requires Python 3.9+. The minimum recommended version is 3.11.

!!! warning
    Support for Python 3.9 ends with lava v8.2 (Kīlauea).

There are two distinct paths for deploying lava, depending on whether the goal
is to:

1.  Run a standalone, locally hosted worker for development,
    experimentation or debugging; or

2.  Run a fully AWS hosted worker.

Both options require the core realm / worker AWS components, such as the,
[DynamoDB tables](#dynamodb-tables) and worker SQS queues. The first option
assumes the lava worker will run on the local desktop and hence does not require
any AWS EC2 compute resources. The second option assumes the lava worker will be
running on one or more EC2 instances.

A lava realm can simultaneously contain workers of both types.

Let's compare the two options in more detail.

||Local Install|AWS Hosted|
|-|-|-|
|Lava repo|Not required. Use pre-built components.|Required.|
|Realm AWS components|Required.|Required.|
|Worker AWS components|Minimal (worker SQS queue, KMS keys, S3 etc). No EC2.|Required, including IAM, EC2 etc.|
|Worker compute|Local PC native (macOS, Linux) or one of the pre-built lava docker images. See [Running Lava in Docker](#running-lava-in-docker).|AWS EC2 instances based on the [lava AMI](#the-lava-ec2-ami).|
|Worker code deploy|Basically `pip install` or `docker run`. See [Desktop Lava Workers](#desktop-lava-workers) and [Docker Based Lava Workers](#docker-based-lava-workers).|A fully self-contained lava code bundle is placed in S3 for workers to find and install on boot. No `pip install`. Can't have production hanging on PyPI.|
|Worker startup|Manual.|Fully automated.|
|Worker security|Permissions determined by the desktop user's AWS IAM profile.|Permissions determined by dedicated IAM components created for the realm / worker.|
|Suitable for production|No.|Yes.|
|Suitable for multi-user|No.|Yes.|
|AWS Costs|Negligible for light usage.|Primarily EC2 costs.|

A quick navigator for both install options is provided below. Subsequent
sections provide a lot more detail.

=== "Local Install"
    Installation of a locally hosted lava worker follows these steps:

    1.  [Create a lava realm](#creating-a-lava-realm).
    2.  [Create a lava worker](#creating-a-lava-worker). Follow the instructions
        for either a desktop worker or docker based worker, as appropriate.

    This path does not require the lava repo to be cloned. Pre-built versions of
    the required components are provided, either from PyPI, or as part of a
    [release on GitHub](https://github.com/jin-gizmo/lava/releases).

=== "AWS Hosted Install"

    Installation of lava involves the following steps:
    
    1.  Clone the [lava repo](#the-lava-repo) and
        [initialise the build area](#getting-started-with-the-repo).
    2.  [Download the Oracle client binaries](#oracle-client-binaries).
    3.  [Build the code bundles](#building-lava-components).
    4.  [Deploy the code bundles](#deploying-lava-components).
    5.  [Build the lava EC2 AMI](#the-lava-ec2-ami).
    6.  [Create a lava realm](#creating-a-lava-realm).
    7.  [Create a lava worker](#creating-a-lava-worker). Follow the instructions
        for creating an EC2 based worker.

    This path does require the lava repo to be cloned. The repo provides 
    automation for elements of the deployment process, including creating the
    required artefact layout in S3.

----
