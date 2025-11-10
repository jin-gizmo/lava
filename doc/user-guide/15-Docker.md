
# Lava and Docker

Lava can use docker in distinct, but related ways:

1.  Lava can run docker container based jobs using the
    [docker job type](#job-type-docker).

2.  The lava programs (worker, dispatcher and other tools) can run in a docker
    container.

3.  The lava code bundle can be built for various target Linux versions inside
    docker containers.

## Running Docker in Lava

The [docker job type](#job-type-docker) runs a docker container
in more or less the same way that it runs [exe](#job-type-exe)
and [pkg](#job-type-pkg) jobs. In the former case, the payload
is obtained as a docker image and in the latter cases as an executable or code
bundle loaded from S3.

### Handling of Temporary Files in Docker Jobs { data-toc-label="Temporary Files" }

The lava worker maps the temporary area for the job into the container and makes
an additional environment variable, `LAVA_TMP`, available to point to it.
Anything written to this area in the container will appear on the host. This can
be useful with [chain](#job-type-chain) jobs as all jobs in the
chain share the same temporary area on the lava worker.

### Handling of Container Logs { data-toc-label="Container Logs" }

The container uses the default container logging configuration. Logs are
collected by the lava worker and uploaded to the realm temporary area in S3
unless the worker is running with the `--dev` option. In that case the logs are
emitted locally on the worker.

### Exit Status

Lava assumes that a zero exit status from the container indicates that the job
has succeeded. This will trigger any `on_success` job actions.

A non-zero exit status indicates to lava that the job has failed. This will
trigger any `on_fail` actions.

### Connection Handling for Container Based Jobs { data-toc-label="Connection Handling" }

Connections to external resources are implemented as small executables created
by lava which are mapped into the container and invoked within the container
in the same way that they would be for an [exe](#job-type-exe)
or [pkg](#job-type-pkg) job.

Refer to [the relevant
section](#connection-handling-for-executable-jobs) in
the chapter on [developing lava jobs](#developing-lava-jobs) for
more information.

This mechanism should work with any Linux based container provided that the
required CLI components are installed in the container. So for example, if a
Postgres connector is required, the container must have the **psql** CLI
installed.

An easy way to ensure the required components are installed is to use one of
the *full* [docker images for lava](#docker-images-for-lava).
These images contain most, if not all, of the CLI components required for lava
supported connection types.

Python executables running in a docker container based on one of the [docker
images for lava](#docker-images-for-lava) can use the connection
manager directly as described in [the relevant
section](#connection-handling-for-python-based-jobs) in the
chapter on [developing lava jobs](#developing-lava-jobs). It is
important to ensure that `/usr/local/lib/lava` is on the `PYTHONPATH` for the
executable in the container.

## Running Lava in Docker

The lava worker, dispatch and events viewer executables can themselves run in a
docker container. The [docker images for
lava](#docker-images-for-lava) have lava pre-installed.

## The Docker Registry

Lava obtains container images from a docker registry. The following registry
options are supported:

*   AWS ECR (recommended)
*   Private docker registries
*   Public registries.

The lava connection manager handles the process of connecting to docker servers
and docker registries. The [docker connection
ID](#connector-type-docker) can be specified at the job level
or the realm level. A value specified at the job level will take precedence.

By default, an AWS EC2 based lava worker has permissions to pull images from the
following ECR repositories:

*   `dist/lava/*` (legacy reasons)
*   `lava/<REALM>/*`

## Docker Images for Lava

!!! note
    As of version 8.1.0 (Kīlauea), lava supports multi-platform images suitable
    for use on both ARM (`linux/arm64`) and x86 (`linux/amd64`).

Lava comes with some standard docker images that have the lava code and other
essential components pre-installed. Currently available image types are:

|Image name|Description|
|-|----|
|`ghcr.io/jin-gizmo/lava/<OS>/base`|A base installation of lava but without the external components required to use CLI based connectors.|
|`ghcr.io/jin-gizmo/lava/<OS>/full`|A full installation of lava that includes the external components required to use CLI based connectors.|

Images are tagged `latest`. A tag matching the version of the lava code is also
applied.

Currently available O/S types for the lava images are:

|O/S|Description|
|-|------------|
|amzn2023|An [Amazon Linux 2023](https://docs.aws.amazon.com/linux/al2023/ug/container.html) based image. The *full* version of the image includes all CLI based connectors, including Oracle sql\*plus.|
|ubuntu24|A standard [Ubuntu Linux 24.04](https://www.ubuntu.com) (LTS) based image. The *full* version of the image includes all CLI based connectors, including Oracle sql\*plus.|

!!! info
    They all have the following as of v8.1 (Kīlauea)

    * Python 3.12
    * OpenSSL 3 or later
    * AWS CLI version 2

Instructions on building the images can be found in the section on
[lava installation](#building-the-lava-docker-images).
