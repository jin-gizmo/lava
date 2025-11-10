
## Job type: docker

The **docker** job type launches a docker container on the worker node and runs
the nominated command. Refer to the [chapter on docker](#lava-and-docker) for
more information.

Lava will connect to a [docker registry](#the-docker-registry), pull the
specified image from a repository and use it to create and run a container with
the specified command. If no command is specified, the default entry point for
the container will be used.

The logs from the container will be captured and, if non-empty, placed into the
realm `s3_temp` area as `<s3_temp>/<job_id>/<run_id>/logs`.

If the command returns a zero exit status the job is considered to have
succeeded. A non-zero exit status indicates failure.

### Payload

The payload is the container repository and, optionally, tag in the form
`repository[:tag]`. If the tag is not specified, a tag of `latest` is used.

### Environment

The following variables are placed into the environment for the container.

|Variable|Description|
|-|-------------------------------------------------------------|
|LAVA_JOB_ID|The `job_id`.|
|LAVA_OWNER|The value of the `owner` field from the job specification.|
|LAVA_REALM|The realm name.|
|LAVA_RUN_ID|The `run_id` UUID.|
|LAVA_S3_KEY|The identifier for the KMS key needed to write data into the S3 temporary area.|
|LAVA_S3_PAYLOAD|The payload location for this job.|
|LAVA_S3_TMP|The private S3 temporary area for this job run. The executables are allowed to put data here.|
|LAVA_TMP|The temporary directory on the host worker node is mapped into the container at this location.|
|LAVA_WORKER|The worker name.|

### Docker Runtime Configuration

The container is run with the following run-time attributes:

1.  Environment variables as described above.

2.  The local temporary area on the worker node is mapped inside the container
    and its location is made available as the `LAVA_TMP` environment variable.
    The container can read and write this directory as for other lava jobs. This
    can be useful for [chain](#job-type-chain) jobs as they
    share the same temporary directory.
    
3.  The container runs with the user ID (uid) set to the effective uid (euid)
    of the lava worker unless overridden by the `host_config` in the job
    specification. **Don't** do this unless you know what you're doing.
    
4.  The effective group ID (egid) of the lava worker is added to the list of
    group IDs for the container unless overridden by the `host_config` in the
    job specification. **Don't** do this unless you know what you're doing.
    
5.  Unless otherwise specified in the `host_config` job parameter, the default
    host configuration (memory, CPU, ports etc) is used.

6.  Stderr and stdout are captured by the lava worker.

7.  The container will use any proxy configuration present in the docker client
    configuration file.

8.  Unless otherwise specified in the `host_config`, the hostname of the
    container is set to `lava-<REALM>-<WORKER>-<RUN_ID>`.

9.  Unless otherwise specified in the `host_config` job parameter, the working
    directory is set to the temporary directory shared between host and
    container. This mimics the behaviour of other executable job types. The
    lava worker will clean up this area on job completion.

### Parameters

|Parameter|Type|Required|Description|
|-|-|-|-------------------------------------------------------------|
|args|List[String]|No|A list of additional arguments for the command. Ignored if no command is specified.|
|command|String|No|The command to run in the container. This will be parsed using standard Linux shell lexical analysis to determine the executable and arguments. If not specified, the default entry point for the container is used.|
|connections|Map[String,String]|No|A dictionary with keys that are connection labels and the values are conn_id|
|docker|String|No|The `conn_id` for [connecting to docker](#connecting-to-docker). If not specified, a value must be specified for the entire realm in the [realms table](#the-realms-table).|
|env|Map[String,String]|No|A map of additional environment variables for the container.|
|host_config|Map[String,\*]|No|A map of container [host configuration parameters](#container-host-configuration).|
|jinja|Boolean|No|If `false`, disable Jinja rendering of the `args`. Default `true`.|
|timeout|String|No|By default, containers run by **docker** jobs are killed 10 minutes after the container starts to run. This parameter can override that with values in the form `nnX` where `nn` is a number and `X` is `s` (seconds), `m` (minutes) or `h` (hours). Note that the timeout must be less than the visibility timeout on the worker SQS queue minus the time to pull the image and start the container.|
|vars|Map[String,\*]|No|A map of variables injected when the command arguments and environment are rendered.|

### Connecting to Docker

Lava needs to be able to connect to a docker daemon to create containers and a
docker registry to obtain docker images. Like all connections in lava, this is
managed through the connection manager.

When running a **docker** job, the process to obtain the specified image is:

1.  Look for a `docker` connection ID in the job parameters. If not found there,
    look for a `docker` connection ID in the realm specification from the
    [realms table](#the-realms-table).

2.  Fetch the daemon and registry connection details from the
    [connections table](#the-connections-table).

3.  Connect to the docker daemon.

4.  Login to the docker registry and pull the required image from the
    specified registry.

Refer to the section on the
[docker connector](#connector-type-docker) for more
information.

### Container Host Configuration

The `host_config` parameter in the docker job specification is a map that allows
a number of configuration parameters for the container to be specified. The
definition and types of these parameters correspond to like named parameters of
the
[containers.run()](https://docker-py.readthedocs.io/en/stable/containers.html)
function of the
[Docker SDK for Python](https://docker-py.readthedocs.io/en/stable/index.html).

The following parameters are permitted:

*   blkio_weight
*   blkio_weight_device
*   cap_add
*   cap_drop
*   cpu_count
*   cpu_percent
*   cpu_period
*   cpu_quota
*   cpu_shares
*   cpuset_cpus
*   cpuset_mems
*   device_read_bps
*   device_read_iops
*   device_write_bps
*   device_write_iops
*   dns
*   dns_opt
*   dns_search
*   domainname
*   extra_hosts
*   hostname
*   group_add
*   mem_limit
*   mem_swappiness
*   memswap_limit
*   nano_cpus
*   network_disabled
*   network_mode
*   ports
*   publish_all_ports
*   shm_size
*   user
*   working_dir

So, for example, to allow a container to use CPUs 0 and 1, disable networking in
the container and set the working directory to `/tmp/lava` add the following:

```json
{
  "parameters": {
    "host_config": {
      "cpuset_cpus": "0,1",
      "network_disabled": true,
      "working_dir": "/tmp/lava"
    }
  }
}
```

### Jinja Rendering of the Arguments and Environment

The collected arguments for the command and any environment values defined in
the job specification are individually rendered using
[Jinja](http://jinja.pocoo.org) prior to execution.

Refer to [Jinja Rendering in Lava](#jinja-rendering-in-lava)
for more information.

The following variables are made available to the renderer.

|Name|Type|Description|
|-|-|-------------------------------------------------------------|
|globals|dict[str,\*]|The `globals` from the job specification updated with any globals received in the job dispatch.|
|job|dict[str,\*]|The [augmented job specification](#the-augmented-job-specification).|
|realm|dict[str,\*]|The realm specification.|
|start|datetime|The local time when the job run started.|
|state|dict[str,\*]|A dictionary of the state items imported into the job, keyed on state_id. The default values are updated at run-time with any current values obtainable from the [state](#the-state-table) table.|
|ustart|datetime|The UTC time when the job run started.|
|utils|dict[str,runnable]|A dictionary of [utility functions](#jinja-utility-functions) that can be used in the Jinja markup.|
|vars|dict[str,\*]|A dictionary of variables provided as the `vars` component of the job `parameters`.|

### Connection Handling

Connections are handled similarly to the
[exe job type](#job-type-exe). In the case of a docker job, the
connection handler executables are mapped into the container and are invoked in
the same way.

Python executables running in a docker container based on one of the [docker
images for lava](#docker-images-for-lava) can use the connection manager
directly as described in [the relevant
section](#connection-handling-for-python-based-jobs) in the chapter on
[developing lava jobs](#developing-lava-jobs).  It is important to ensure that
`/usr/local/lib/lava` is on the `PYTHONPATH` for the executable in the
container.

### Dev Mode Behaviour

Normally, the **docker** job will copy the container logs to S3 on the
conclusion of the job. In dev mode, the container logs are emitted locally after
the job run instead of being copied to S3.

### Examples

The following example will run a shell to invoke the Linux date command in one
of the standard lava docker images. The connection ID for the docker registry
containing the image is `ecr`.

```json
{
  "description": "Run a simple command in a container",
  "dispatcher": "Sydney",
  "enabled": true,
  "job_id": "demo/simple-docker",
  "owner": "demo@somewhere.com",
  "parameters": {
    "args": [
      "-c",
      "date"
    ],
    "command": "/bin/sh",
    "docker": "ecr",
    "timeout": "10s"
  },
  "payload": "jin-gizmo/lava/amzn2023/base",
  "type": "docker",
  "worker": "core"
}
```

This example does exactly the same thing with the docker image and command
specified in a slightly different way.

```json
{
  "description": "Run a simple command in a container",
  "dispatcher": "Sydney",
  "enabled": true,
  "job_id": "demo/simple-docker",
  "owner": "demo@somewhere.com",
  "parameters": {
    "command": "/bin/sh -c date",
    "docker": "ecr",
    "timeout": "10s"
  },
  "payload": "dist/lava/centos8/full:latest",
  "type": "docker",
  "worker": "core"
}
```

And again:


```json
{
  "description": "Run a simple command in a container",
  "dispatcher": "Sydney",
  "enabled": true,
  "job_id": "demo/simple-docker",
  "owner": "demo@somewhere.com",
  "parameters": {
    "command": "/bin/sh -c {{vars.cmd}}",
    "docker": "ecr",
    "timeout": "10s",
    "vars": {
        "cmd": "date"
    }
  },
  "payload": "dist/lava/centos8/full:latest",
  "type": "docker",
  "worker": "core"
}
```
