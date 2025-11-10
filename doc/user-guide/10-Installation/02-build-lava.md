## Oracle Client Binaries

Lava's [oracle](#connector-type-oracle) connector requires the Oracle Instant
Client. The following packages are required:

*   Basic Light or Basic
*   SQL*Plus

The ZIP format for these must be downloaded from
[Oracle](https://www.oracle.com/database/technologies/instant-client/downloads.html)
and placed in `external-packages/oracle` **before any lava components are
built**. There is a particular layout required.  To download or update the
required bundles run the following from the top of the repository.

```bash
make oracle
```

## Building Lava Components

The build process is controlled by GNU *make*. To get help on the build process,
run:

```bash
make help
# ... or ...
make
```

These are the primary build targets controlled from the top level Makefile:

| Target    | Description                                                  |
| --------- | ------------------------------------------------------------ |
| `cfn`     | The [lava CloudFormation templates](#building-the-cloudformation-templates). |
| `preview` | The [lava documentation](#building-the-lava-documentation), including the lava user guide and the API documentation. This will build the user guide and open a browser window to preview it locally. |
| `lambda`  | The [lava Lambda function code bundles](#building-the-lava-lambda-function-code-bundles). |
| `jinlava` | The [jinlava Python package](#building-the-jinlava-python-package). |
| `pkg`     | The lava worker code bundles. Additional parameters on the *make* command control whether the bundle is intended for the [build host](#building-the-lava-worker-bundle-for-the-build-host) or a [foreign host](#building-the-lava-worker-bundle-for-a-foreign-host). |
| `tools`   | The [lava job framework](#building-the-lava-job-framework).  |

These components are built by running *make* in one of the subdirectories:

* the [lava AMI](#the-lava-ec2-ami) (`ami/`)
* [lava docker images](#building-the-lava-docker-images) (`docker/`).

### A Thunder Run for the Reckless { data-toc-label='Thunder Run' }

This is a quick summary of a typical build sequence. ***Please read the full
section*** before launching into this. You, and possibly everyone who tries to
use the mess you create, will be sorry if you don't.

This process will leave lots of artefacts in the `dist` directory.

```bash
# If you are using a private PyPI server, set that here.
# Do not rely on pip.conf.
export PIP_INDEX_URL=...

# Get ready to build.
make init
source venv/bin/activate

# Download the Oracle binaries
make oracle

# Build and preview the user guide because we all read the doco first, right?
make preview

# Make the bits that don't need a builder docker image
make cfn jinlava tools

# Make a couple of builder docker images. This will take quite a while.
# The process does a full Python install from source for ARM and x86.
make builder runtime=amzn2023-py3.11
make builder runtime=amzn2023-py3.13

# Make the lava worker install bundle for multiple runtimes/platforms
# First ... for our build machine.
make pkg
# Now use our builders to build for foreign hosts.
make pkg runtime=amzn2023-py3.11 platform=linux/amd64
make pkg runtime=amzn2023-py3.11 platform=linux/arm64
make pkg runtime=amzn2023-py3.13 platform=linux/amd64
make pkg runtime=amzn2023-py3.13 platform=linux/arm64

# Make the lambda code bundles. These need the amzn2023-py3.13 builder image.
make lambda

# Make the lava docker images. You might want to start this and head off to a
# lunch.
cd docker
make build-all
make check-all
# Make sure the images have been pushed to our local private docker registry.
# This registry is on localhost:5001 and runs in a container.
jindr images
```

### Building the CloudFormation Templates { data-toc-label="Building the CFN Templates" }

!!! note
    Pre-built versions of the CloudFormation templates are provided as part of
    a [release on GitHub](https://github.com/jin-gizmo/lava/releases).

Lava comes with several [CloudFormation templates](#cloudformation-templates) to
build the core components for realms and workers. The sources for these are in
the `cfn` directory. These **are not** deployable as-is. The CloudFormation
templates must be built by doing:

```bash
make cfn
```

This will place ready-to-deploy versions in `dist/cfn/*.cfn.json`. Automatically
generated documentation for these is placed in the same directory as
`dist/cfn/*.cfn.md` and `dist/cfn/*.cfn.html`.

!!! warning
    Once more ... **Do not** deploy CloudFormation templates from the `cfn/`
    directory. It will not work. Deploy only from `dist/cfn`.


| Name                 | Description                                                  |
| -------------------- | ------------------------------------------------------------ |
| [lava-common.cfn.json][lava-commoncfnjson] | Contains the common components that are not realm dependent. This stack needs to be deleted and recreated for each update. This is safe to do. |
| [lava-realm.cfn.json][lava-realmcfnjson] | Contains the worker independent parts for creating a realm. See [Creating a Lava Realm](#creating-a-lava-realm). |
| [lava-worker.cfn.json][lava-workercfnjson] | Contains the worker dependent parts for creating a worker. The realm must already exist. See [Creating a Lava Worker](#creating-a-lava-worker). |

!!! note
    *Generally*, it's not critical for the CloudFormation template minor
    version to match the deployed lava code minor version. Major versions should
    match.

### Building the Lava Worker Bundle for the Build Host { data-toc-label="Building for the Build Host" }

The lava worker bundle is the artefact required for a deployed lava worker. It is
a fully self-contained compressed tar file containing the lava code and includes
all of the required Python packages. As the lava worker uses some C based Python
modules, the build for the lava worker bundle must be done on the same O/S type,
Python version and platform architecture as the target deployment environment.

To create the lava worker code bundle to match the build host:

```bash
make pkg
```

If an alternative PyPI server is being used (e.g. a Sonatype Nexus instance),
set the environment variable `PIP_INDEX_URL` appropriately:

```bash
PIP_INDEX_URL=... make pkg

# or ...
export PIP_INDEX_URL=...
make pkg
```

The build artefacts are placed in the `dist` directory as:

```bare
dist/pkg/<OS>/lava-<LAVA-VERSION>-<OS>-<PYTHON-VERSION>-<ARCHITECTURE>.tar.bz2
```

e.g.

```bare
dist/pkg/amzn2023/lava-8.1.0-amzn2023-py3.11-aarch64.tar.bz2
                             ^^^^^^^^^^^^^^^ ^^^^^^^
                               "runtime"    "platform" (as the host defines itself)
```

### Building the Lava Worker Bundle for a Foreign Host { data-toc-label="Building for a Foreign Host" }

!!! note
    This process has changed in version 8.1 (Kīlauea). It is now possible to
    build lava worker bundles for different runtimes and architectures using
    [Docker Desktop](https://www.docker.com/products/docker-desktop/) on macOS.
    The process has not been tested on other environments although it uses only
    docker standard multi-platform build capabilities.

First, terminology:

* **Runtime**: The operating system type + Python version (e.g. `amzn2023-py3.11`)
* **Platform**: hardware architecture. 
* **Foreign host**: A host that differs in *runtime* or *platform* from the build host

Platform terminology is quite varied, depending on context:

| Platform | O/S terminology                      | Docker terminology | Oracle S/W |
| -------- | ------------------------------------ | ------------------ | ---------- |
| x86      | `x86_64`                             | `linux/amd64`      | `x86`      |
| ARM      | `arm64` (macOS) or `aarch64` (Linux) | `linux/arm64`      | `arm64`    |

To run a lava worker bundle on a host, the **runtime and platform must match**.
The build process described
[above](#building-the-lava-worker-bundle-for-the-build-host) assumes the bundle
will be deployed on a machine with the same runtime and platform as the build
machine.

A foreign host build uses a docker container based on a *builder* image. The
builder images support both x86 and ARM architectures using docker
multi-platform builds.

The process involves two steps:

1. [Build the builder image](#building-the-builder-image).
2. [Use the builder image](#using-the-builder-image) to build the lava worker
   bundle.

#### Building the builder image

The docker builder image defines the runtime and platform for the lava worker
bundle it produces.

The process for "building the builder" is:

```bash
make builder runtime=<RUNTIME>
# e.g.
make builder runtime=amzn2023-py3.11
```

This will build a multi-platform docker image supporting both `linux/amd64` and
`linux/arm64` and push it to the [local docker
registry](#the-local-docker-registry). The image name is:

```bare
localhost:5001/build/lava/<RUNTIME>:latest
```

e.g.

```bare
localhost:5001/build/lava/amzn2023-py3.11:latest
```

!!! note
    The builder images incorporate a Python installation built from source (for
    two different platforms) to ensure consistency. This can take a reasonable
    amount of time. Be patient.

To see which builders are available in the local docker registry:

```bash
jindr images
```

Check the `etc/builders` directory for a list of
supported foreign runtime types. The following are currently available:

| Runtime           | Operating System  | Python Version | Deprecated |
| ----------------- | ----------------- | -------------- | ---------- |
| `amzn2023-py3.9`  | Amazon Linux 2023 | 3.9            | Yes        |
| `amzn2023-py3.11` | Amazon Linux 2023 | 3.11           |            |
| `amzn2023-py3.12` | Amazon Linux 2023 | 3.12           |            |
| `amzn2023-py3.13` | Amazon Linux 2023 | 3.13           |            |
| `rocky9-py3.9`    | Rocky Linux 9     | 3.9            | Yes        |

#### Using the builder image

To build the bundles for a foreign host, first build the appropriate [builder
image](#building-the-builder-image), then:

```bash
make pkg runtime=<RUNTIME> platform=<PLATFORM>
# e.g.
make pkg runtime=amzn2023-py3.11 platform=linux/amd64
```

Once again, set `PIP_INDEX_URL` if an alternative PyPI server is being used:

```bash
PIP_INDEX_URL=... make pkg runtime=<RUNTIME> platform=<PLATFORM>

# or ...
export PIP_INDEX_URL=...
make pkg runtime=<RUNTIME> platform=<PLATFORM>
```

The built worker bundles are placed in the `dist` directory as:

```bare
dist/pkg/<OS>/lava-<LAVA-VERSION>-<OS>-<PYTHON-VERSION>-<ARCHITECTURE>.tar.bz2
```

### Building the Lava Lambda Function Code Bundles { data-toc-label="Building the Lambdas" }

The lava lambda functions are pure Python and so are not particularly sensitive
to the build platform or runtime. Nevertheless, they are built inside a docker
container derived from the `amzn2023-py3.13` builder image using the
`linux/arm64` platform. This is close enough to the deployed environment.

The build process is:

```bash
make lambda
```

The bundles will be placed in the directory `dist/lambda`.

### Building the Lava Docker Images { data-toc-label="Building the Docker Images" }

Lava comes with a suite of [docker images](#docker-images-for-lava) that are
suitable for use as base images for [docker](#job-type-docker)
jobs. The images can also be used to create containers that run the lava worker
itself.

!!! note
    As of version 8.1 (Kīlauea), multi-platform (ARM and x86) images are built
    by default. Docker pull operations will automatically select the platform
    matching the client host unless overridden.

To build the multi-platform images do the following. The images will be built
and pushed to the [local docker registry](#the-local-docker-registry) at
`localhost:5001`.

```bash
cd docker

# Get help -- lots of build options. Available O/S types will be listed.
make

# Build all of the images. This will push the images to our local
# docker registry at localhost:5001.
make build-all

# Do a fast (and flimsy) health check
make check-all

# ... or ... make a specific O/S (see docker/os directory)
make build os=<OS>
make check os=<OS>

# Check the local registry to see the images are present
jindr images
```
The images can be run locally in the normal way:

```bash
# Run the image that matches the local machine architecture
docker run -it --rm localhost:5001/lava/amzn2023/base

# Specify which platform we want. M-series Macs can run both arm64
# and amd64 (under emulation)
docker run -it --rm --platorm linux/amd64 localhost:5001/lava/amzn2023/base
```

Prior to v8.2 (Kīlauea), the standard lava build process only supported use
of AWS ECR for deploying lava docker images. The images can now be deployed to
ECR or a different registry.

See [Docker Images for Lava](#docker-images-for-lava) for publicly available
docker images.

=== "Deploying to ECR"
    Deploying the images to AWS ECR involves creating the target repositories
    and copying  the images from the [local docker
    registry](#the-local-docker-registry) to ECR.

    First, login to AWS for command line access.

    Create the ECR target repositories, if not already present:

    ```bash
    make ecr-repo os=...
    # ... or do all at once if none of them exist yet.
    make ecr-repo-all
    ```

    This will also apply a lifecycle policy to the repositories to only retain 4
    images, and to remove untagged images after 1 day. If this doesn't suit,
    modify the policy in ECR after the repository has been created.

    Push images to ECR:

    ```bash
    make ecr-push os=<OS>
    # ... or push all at once
    make ecr-push-all
    ```

    The repositories will be created with names of the form
    `dist/lava/<OS>/<TYPE>` (e.g. `dist/lava/amzn2023/base`). These *can* be
    changed if it's critical, but it's best not to. The [IAM
    policies](#lava-iam-policies) created by the supplied [CloudFormation
    Templates](#cloudformation-templates) assume this structure.

    If it's all too much to bear, the `dist` prefix can be overridden, thus:

    ```bash
    make ecr-repo os=... prefix=...
    make ecr-push os=... prefix=...
    ```

    Additional, custom IAM policies will need to be attached to the [lava IAM
    groups](#lava-iam-groups) to provide users with access.

=== "Deploying to another registry"
    Deploying the images to a docker registry involves creating the target 
    repositories (if required by the registry), and copying the images from the
    local docker registry to the target registry.
    
    !!! note
        The examples in this section assume Github Container Registry (ghcr.io)
        for an account named `my-github`.
        Update the examples as appropriate.
    
    First, login to the registry. The makefile will not do that for you.

    ```bash
    # Yes, I know, GHCR ignores the username but you get the idea.
    docker login ghcr.io -u my-github
    ```

    If the target registry requires creation of repositories prior to pushing
    images, that must be done manually. GHCR doesn't require this. Don't forget
    to create a repository for both `base` and `full` images.

    Repositories should be named like so:
    
    ```text
    <PREFIX>/lava/<OS>/base
    <PREFIX>/lava/<OS>/full
    ```

    e.g. The public images are named like so:

    ```text
    ghcr.io/jin-gizmo/amzn2023/base
    ---+--- ----+---- ----+--- -+--
       |        |         |     |
    registry    |         OS    |
             prefix           type
    ```

    Push the images:

    ```bash
    make push registry=ghcr.io prefix=my-github
    ```

### Building the jinlava Python Package

The **jinlava** package is a standard Python package that can be installed using
pip. This is handy when developing lava jobs using an IDE such as PyCharm. Full
API documentation is also available.

The package includes the lava APIs and all of the CLI components and utilities.

To build a source distribution of the **jinlava** package:

```bash
make jinlava
```

In Python programs, this is imported as `lava`:

```python
import lava

print(lava.__version__)
```

### Building the Lava Job Framework

!!! note
    Pre-built versions of the lava job framework are (for now) provided as part
    of a [release on GitHub](https://github.com/jin-gizmo/lava/releases). However,
    the preferred mechanism is to use the [lava-new](#lava-new-utility) instead.

The [lava job framework](#the-lava-job-framework) can be built thus:

```
# From the root of the lava code repo ...
make tools
```

The framework cookiecutter zipped bundle is placed in `dist/dev-tools`.

### Building the Lava Documentation { data-toc-label="Building the Documentation" }

The lava user guide and API documentation can be built thus:

```bash
# From the root of the lava code repo ...
make preview
```

This will create the user guide and open a browser window to preview it. Partial
build artefacts are placed in `dist/doc`.

When published, the user guide is hosted on GitHub Pages. The publishing process
is simply:

```bash
make publish
```

If the user guide is modified, it **must** be spell checked:

```bash
make spell
```

!!! warning
    Failure to check spelling, or, worse, recklessly adding your orthographic
    ignorance to the custom dictionary will result in much wailing and gnashing
    of teeth.
