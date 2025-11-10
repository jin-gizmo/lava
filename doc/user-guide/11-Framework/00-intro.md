
# The Lava Job Framework { x-nav="Lava Job Framework" }

Building and deploying simple lava jobs is fairly straightforward. For more
complex requirements, a lava solution may require multiple jobs with associated
JSON job specifications, connectors and S3 triggers to be tailored and deployed
across multiple lava realms (e.g. dev, test and production). Job payloads also
need to be assembled into packages or docker containers and deployed. This can
be manually intensive and error prone.

The lava job framework provides a suggested way of structuring, building and
deploying lava jobs. Its use is completely optional.

The framework provides the following advantages over hand-crafting a complex
lava solution.

*   Job, connection and s3 trigger specifications can be specified in either
    YAML or JSON in a realm / environment independent way. YAML is easier to
    read, write and annotate than JSON. YAML formatted samples are provided in
    the [Lava Job Framework Samples](#lava-job-framework-samples)
    section.

*   Environment specific information is managed in separate, extensible
    configuration files.

*   The deployable job, connection and s3 trigger specifications and the job
    payloads can be generated and deployed for a target environment in a single
    step.

*   The framework can automatically build and deploy single file
    [exe](#job-type-exe), [sql](#job-type-sql)
    and [sqlc](#job-type-sqlc) payloads, multi-file
    [pkg](#job-type-pkg) payloads and images for
    [docker](#job-type-docker) jobs. It could be readily
    integrated into a CI/CD pipeline.

The framework uses a combination of the following common tools:

*   [cookiecutter](https://pypi.python.org/pypi/cookiecutter)

*   [GNU make](https://www.gnu.org/software/make/)

*   [Jinja](https://jinja.palletsprojects.com/) rendering

*   The [AWS CLI](https://aws.amazon.com/cli/).

It works on Linux and macOS. It can also run inside a docker container, with
some limitations. It is not supported on DOS.
