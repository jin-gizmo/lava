### Docker Payloads

!!! warning
    Lava version 8.1 (Kīlauea) introduced some important changes in this area.
    It is *essential* to read [Backward Compatibility Notes for Docker
    Payloads](#compatibility-notes-for-docker-payloads) if running an earlier
    version.

Directories directly under `lava-payloads` with names ending in `.docker` are
assumed to contain the code for lava [docker](#job-type-docker)
jobs.

The build process is essentially:

1.  Create a clean copy of the source tree.

2.  Any files in the `env/` directory of the source tree are Jinja rendered
    using the environment configuration file. This provides one possible
    mechanism to include environment specific information in the build.

3.  Any Jupyter notebooks (`*.ipynb`) are converted to Python.

4.  If the source directory already contains a `Dockerfile`, that will be Jinja
    rendered using the environment configuration file and used to build the
    image.

5.  If the source directory does not contain a `Dockerfile`, a
    [default](#the-default-dockerfile) one is used.

!!! info
    These components are placed in the container in `/lava` and owned by the
    user `lava`. However, by default, the container will be run with the
    effective user ID of the lava worker. This is required so that any items
    left by the container in the $LAVA_TMP area can be read by the worker. Take
    care when building containers to account for the different user IDs at build
    and run time.

The install process will create an appropriate ECR repo and push the image. The
uninstall process will delete the ECR repo.

#### The Default Dockerfile

The default `Dockerfile` supplied with the framework should suffice in most
cases. It effectively emulates the packaging process for pkg payloads but builds
a docker image instead of a zip file.

The payload files are installed in the `/lava` directory in the container. The
files are owned by root and are globally readable inside the container. Any
files that are user executable in the source directory are made globally
executable inside the container.

!!! info
    The `/lava` directory is **not** added to any `*PATH` environment
    variables by default.

If the root directory of the source tree contains a `requirements.txt` file,
then Python modules listed therein, including any dependencies, are installed as
part of the image build. If the root directory contains a
`requirements-nodeps.txt` file, then Python modules listed therein, excluding
any dependencies, are included.

If the default `Dockerfile` is not adequate, a custom one can be created. A
simple `Dockerfile` might look something like the following, but keep in mind
the [runtime configuration](#docker-runtime-configuration) to ensure permissions
are set correctly inside the container when building the image.

```
FROM ghcr.io/jin-gizmo/lava/amzn2023/base

# Copy our code into the image
COPY * /install/

# Point at the right pip repo. The Makefile will supply the value.
ARG PIP_INDEX_URL
ENV PIP_INDEX_URL $PIP_INDEX_URL

RUN \
	cd /install ; \
    echo My code is here ; \
    ls -lR : \
	python3 -m pip install -r requirements.txt --upgrade
```

#### Docker Platform Architecture Selection

As of version 8.1 (Kīlauea), the lava job framework supports building docker
payload images for a specific target platform architecture.

!!! info
    Currently, the capability to generate cross-platform images is only supported
    when using Docker Desktop with multi-platform support enabled.

Image platform selection is controlled by the `docker->platform` key in the
environment configuration file. This key may have one of the following values.

|Docker platform|Description|
|--|-----------------|
|`host`|Use the default behaviour of the build host docker platform. The platform selected will be dependent on some combination of the architecture of the base image and the build host, as is usual for docker.|
|`linux/amd64`|Build an image for x86\_64 platforms.|
|`linux/arm`|Build an image for ARM platforms, such as Mac M series and AWS Graviton.|
| unspecified|Build an image for x86\_64 platforms.|

For a cross-platform build to work as expected, the base image must either be a
multi-platform image or have itself been built for the target platform. Most
standard operating system base images, such as Amazon Linux 2023 and Ubuntu 
Linux are multi-platform. As of version 8.1 (Kīlauea), the [lava docker
images](#docker-images-for-lava) are also multi-platform.

####  Compatibility Notes for Docker Payloads

This is a bit complicated but please bear with me ...

To understand platform compatibility when deploying a docker payload, the
fundamental principle is that **the docker image must contain a platform version
that matches the host running the lava worker**.

If lava workers are being run on x86 AWS EC2 instances
(`linux/amd64` in docker terminology), job payload docker images must be, or
contain, a `linux/amd64` version.

This, in turn, implies that the base image for the payload is either:

1.  A single platform `linux/amd64` image; or

2.  A multi-platform image that

    *   includes a `linux/amd64` platform version; *and*
    *   the build process, implicitly or explicitly, directs the use of the
        `linux/amd64` platform version.

If every machine in the dev / build / run chain is x86, no problems. That was
the world view for lava versions prior to version 8.1. The [lava docker
images](#docker-images-for-lava), commonly used as payload base images, were
built only for x86. Any derived images would inevitably be x86.

Unfortunately, if a multi-platform base image, such as any of the common
operating system base images, was used on a M-series Mac build machine, the
result would be an ARM (`linux/arm64`) payload which would not run on an x86 AWS
EC2 worker. The lava job framework provided no way to specify what output
architecture was required.

It also meant that the [lava docker images](#docker-images-for-lava) could not
run on ARM machines, except under emulation.

Lava version 8.1 (Kīlauea) introduced some key changes in this area:

1. The [lava docker
   images](#docker-images-for-lava) are multi-platform images supporting x86
   (`linux/amd64`) and ARM (`linux/arm64`).

2.  The lava job framework includes the ability to explicitly specify the target
    platform for docker payloads, rather than relying on some implicit
    combination of the platform types available in the base image and the
    platform type of the build host.

So far, so good.

New projects using the v8.1 lava job framework allow the user to control the
target platform using the `docker->platform` key in the environment
configuration file. It defaults to `linux/amd64`. This should work fine on x86
and M-series Mac build machines using [Docker
Desktop](https://docs.docker.com/desktop/) with emulation.

*What happens when working with existing projects using an older version of the
lava job framework?* I hear you ask. It depends:

1. Existing, deployed docker payloads and projects without docker payloads.    
   *No impact.*

2. Rebuilding and deploying docker payloads from an x86 build host.    
   *No impact.*

3. Rebuilding and deploying from an ARM build host (e.g. M-series Mac)    
   *This (probably) would have worked prior to v8.1. Now, it will not. The lava
   job framework version must be updated to v8.1 (or later). See [Updating the
   Framework in an Existing
   Project](#updating-the-framework-in-an-existing-project). The
   `docker->platform` key should be added to the `config/*.yaml` files, but will
   default to `linux/amd64` if not present.*
