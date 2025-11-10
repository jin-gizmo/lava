
##  Connector type: docker

The **docker** connector manages access to a docker daemon and docker
registry for use with [docker](#job-type-docker) jobs.

Lava supports the following registry options:

*   AWS ECR
*   Private docker registries
*   The standard docker public registry.

|Field|Type|Required|Description|
|-|-|-|-------------------------------------------------------------|
|conn_id|String|Yes|Connection identifier.|
|description|String|No|Description.|
|email|String|No|Email address for registry login.|
|enabled|Boolean|Yes|Whether or not the connection is enabled.|
|password|String|No|Name of the SSM parameter containing the password for authenticating to the registry. Required for private docker repositories. Ignored for ECR registries. For a given `<REALM>`, the SSM parameter name must be of the form `/lava/<REALM>/...` and the value must be a secure string encrypted using the `lava-<REALM>-sys` KMS key.|
|registry|String|No|Either the URL for a standard registry or `ecr[:account-id]`. In the latter case, lava will connect to the AWS ECR registry in the specified AWS account or the current account if no `account-id` is specified. If no registry is specified, the default public docker registry is used.|
|server|String|No|URL for the docker server. If not specified, then the normal docker environment variables are used. Generally, this means using the local docker daemon accessed via the UNIX socket.|
|timeout|Number|No|Timeout on docker API calls in seconds.|
|tls|Boolean|No|Use TLS when connecting to the docker server. Default True.|
|type|String|Yes|`docker`.|
|user|String|No|User name for authenticating to the registry. Required for private docker repositories. Ignored for ECR registries.|


### Accessing External Registries

Lava prefers to obtain its docker images from the local AWS ECR. It's safer,
simpler and more robust than relying on external registries to provide safe,
secure code at run-time, particularly for a production environment.

!!! tip
    If you need to use an external image, copy it to the local AWS ECR and use
    it from there. The [lava job framework](#the-lava-job-framework) will
    place the built payloads for docker jobs in ECR. A trivial Dockerfile can
    copy an external image as part of the build process.

If you must do this damn fool thing, lava permits it. There are some considerations:

1.  **Private registries** (i.e. requiring authentication to access) will
    require a connection specification as described above, including the 
    registry identifier and credentials. The registry will also be part of the
    image name as usual.

2.  **Public registries**, such as Docker Hub and public repositories on GitHub
    Container Registry (GHCR), can be addressed by a common connection
    specification containing neither registry, nor credentials. The registry
    will be part of the image name as usual (except for Docker Hub which is the
    default registry).

3.  **Proxies** can be a problem. Lava will not help you here. The docker daemon
    proxy configuration will need to be handled at the platform level, however
    that is done.

### Examples

=== "ECR Connector"

    This is the standard connection specification for the local AWS ECR.

    ```json
    {
        "type": "docker",
        "conn_id": "docker/ecr",
        "description": "Docker ECR connection",
        "enabled": true,
        "registry": "ecr",
    }
    ```

=== "Public Registries"

    This connection specification should handle most public registries.

    ```json
    {
        "type": "docker",
        "conn_id": "docker/public",
        "description": "Docker basic connection (covers public repos)",
        "enabled": true
    }
    ```

=== "Private Registries"

    This connection specification is for a private registry on the
    Github Container Registry:

    ```json
    {
        "type": "docker",
        "conn_id": "docker/ghcr/xyzzy",
        "description": "Github Container Registry for user xyzzy",
        "enabled": true,
        "registry": "ghcr.io"
        "user": "not-used-by-ghcr",
        "password": "/lava/my-realm/ghcr/xyzzy/access-token"
    }
    ```
