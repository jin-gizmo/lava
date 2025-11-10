
##  Docker in the Build Process

Docker is used as part of the build process for a number of lava components,
either because of a requirement to match the characteristics of the target
deployment environment, need for specialised tools, or because the build product
itself is a docker artefact.

Components that use docker as part of the build process include:

* the [lava worker installation bundle](#building-the-lava-worker-bundle-for-a-foreign-host)
* the [lava docker images](#docker-images-for-lava)
* the lava Lambda functions
* lava tests for docker based resources (databases etc).

This has all been developed using [Docker
Desktop](https://www.docker.com/products/docker-desktop/) on macOS. Your mileage
may vary on other platforms. These are the suggested settings in [Docker
Desktop](https://www.docker.com/products/docker-desktop/) on macOS.

![](img/docker-config.png)

### The Local Docker Registry

The build process sometimes requires multi-platform docker images to provide
both x86 and ARM support. This in turn requires a docker registry to which these
multi-platform images can be pushed as part of the build process. Unlike single
platform images that can be built and then pushed to a registry in separate
steps, multi-platform images *must* be built and pushed in a single step.

The lava build process will start a local docker registry in a container as, and
when, required as `localhost:5001`. This is managed using the **jindr** tool
which is installed as part of the [lava repo setup](#getting-started-with-the-repo).

```bash
jindr --help
# Start the local registry manually, if required
jindr start
# The registry will continue to run until manually stopped
jindr stop
# List the images in the registry
jindr images
# Copy an image to ECR (latest + 8.1.0 tags)
jindr copy2ecr localhost:5001/build/lava/amzn2023-py3.11:latest 8.1.0
```
