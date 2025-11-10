
## Creating Payloads

Some job types, such as
[cmd](#job-type-cmd),
[dag](#job-type-dag) and
[sqli](#job-type-sqli), have the payload fully contained within
the [job specification](#the-jobs-table).

For other job types, such as 
[exe](#job-type-exe),
[pkg](#job-type-pkg) and
[sql](#job-type-sql), the payload is external to the
[job specification](#the-jobs-table), which references the
payload content (e.g. as a code bundle in S3 or a docker image repository).
For these, the `lava-payloads` directory will contain the source for the lava
payloads for the project. The framework currently supports automated build for
the following external payload types:

*   Python scripts (`*.py`)

*   Jupyter notebooks (`*.ipynb`)

*   Shell scripts (`*.sh`)

*   SQL scripts (`*.sql`)

*   [Packages](#pkg-payloads) for
    [pkg](#job-type-pkg) jobs (`*.pkg/`).

*   [Docker images](#docker-payloads) for
    [docker](#job-type-docker) jobs (`*.docker/`).
    
*   [Resource directories](#resource-directories)
    (`*.rsc` and `*.raw`).
