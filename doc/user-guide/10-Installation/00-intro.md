
# Lava Installation and Operation { x-nav="Installation & Operation" }

There are distinct paths for deploying lava, depending on whether the goal
is to:

* Run a standalone, locally hosted worker for development,
  experimentation or debugging; or

* Run a fully AWS hosted worker.

All options require the core realm / worker AWS components, such as the,
[DynamoDB tables](#dynamodb-tables) and worker SQS queues. They vary in how these components are provided and where the lava worker is hosted. At a high level, the options are:

1. **Lava Sandbox**: An entire functional lava environment, including the AWS components and the lava worker, runs locally in docker containers. A single CLI command starts the environment.
2. **Local Install:** The AWS components need to be installed in AWS, or the sandbox can be used. The lava worker runs locally, either using a pre-built docker image, via `pip install` or natively from the repo.
3. **AWS Hosted:** The AWS components need to be installed in AWS and the lava worker runs in AWS on one or more EC2 instances.

Let's compare the options in more detail.

||Sandbox|Local Install|AWS Hosted|
|-|-|-|-|
|Lava repo|Not required.|Not required.|Required.|
|Realm AWS components|Pre-packaged in docker|Required.|Required.|
|Worker AWS components|Pre-packaged in docker|Minimal (worker SQS queue, KMS keys, S3 etc). No EC2.|Required, including IAM, EC2 etc.|
|Worker compute|Pre-packaged in docker|Local PC native (macOS, Linux) or one of the pre-built lava docker images. See [Running Lava in Docker](#running-lava-in-docker).|AWS EC2 instances based on the [lava AMI](#the-lava-ec2-ami).|
|Worker code deploy|Pre-packaged in docker|`pip install` or `docker run`  or directly from the repo . See [Desktop Lava Workers](#desktop-lava-workers) and [Docker Based Lava Workers](#docker-based-lava-workers).|A fully self-contained lava code bundle is placed in S3 for workers to find and install on boot. No `pip install`. Can't have production hanging on PyPI.|
|Worker startup|Docker compose|Manual.|Fully automated.|
|Worker security|N/A - Local only|Permissions determined by the desktop user's AWS IAM profile.|Permissions determined by dedicated IAM components created for the realm / worker.|
|Suitable for production|No.|No.|Yes.|
|Suitable for multi-user|No.|No.|Yes.|
|AWS Costs|None.|Negligible for light usage.|Primarily EC2 costs.|

A quick navigator for the install options is provided below. Subsequent
sections provide a lot more detail.

=== "Sandbox"
    Download the docker compose file from GitHub and run it. Job done.

    See [The Lava Sandbox](#the-lava-sandbox) for details.

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
