"""Lava docker connector."""

from __future__ import annotations

import subprocess
from base64 import b64decode
from typing import Any

import boto3
import docker

from lava.common import get_lava_param
from lava.lavacore import IGNORE_FIELDS, LavaError
from lava.lib.misc import dict_check
from .core import CONNECTION_REQUIRED_FIELDS, LOG, get_connection_spec

__author__ = 'Murray Andrews'

DOCKER_CONNECTION_REQUIRED_FIELDS = CONNECTION_REQUIRED_FIELDS

# TODO: We have a potential login race condition in here if two threads try to
#       login at the same time. Because of the way docker works, it is actually
#       very tricky to fix in the general case. Ideally, each job (or possibly
#       worker thread) would be using a different `dockercfg_path`. To do that
#       we'd need to pass the job tmpdir in or make the connection creator a
#       context manager (which is not a bad idea anyway).
#       Gnarly.


# ------------------------------------------------------------------------------
def get_docker_registry_credentials(
    conn_spec: dict[str, Any], aws_session: boto3.Session = None
) -> dict[str, Any]:
    """
    Extract docker registry credentials from a connection spec.

    :param conn_spec:       Connection spec
    :param aws_session:     A boto3 Session(). If not specified a default will be
                            created.

    :return:                A dictionary of parameters suitable for use with the
                            docker client login() call.
    """

    if not aws_session:
        aws_session = boto3.Session()

    registry = conn_spec['registry']  # type: str

    if registry != 'ecr' and not registry.startswith('ecr:'):
        # Standard registry login
        dict_check(conn_spec, required={'user', 'password'})
        return {
            'registry': registry,
            'username': conn_spec['user'],
            'password': get_lava_param(conn_spec['password'], aws_session=aws_session),
            'email': conn_spec.get('email'),
        }

    # ----------------------------------------
    # AWS ECR

    ecr = aws_session.client('ecr')

    registry_ids = registry.split(':')[1:]

    if registry_ids:
        auth_data = ecr.get_authorization_token(registryIds=registry_ids)
    else:
        auth_data = ecr.get_authorization_token()

    server = auth_data['authorizationData'][0]['proxyEndpoint']  # type: str
    if server.startswith('https://'):
        server = server[8:]

    user, password = (
        b64decode(auth_data['authorizationData'][0]['authorizationToken'])
        .decode('utf-8')
        .split(':', 1)
    )

    return {
        'registry': server,
        'username': user,
        'password': password,
        'email': conn_spec.get('email'),
    }


# ------------------------------------------------------------------------------
def get_docker_connection(
    conn_id: str, realm: str, aws_session: boto3.Session = None
) -> docker.DockerClient:
    """
    Get a docker client connection with a login to a registry.

    The caller is expected to close it when done. Connection type must be
    `docker`.

    Allowed connection params are:

    - `registry`:
        Either hostname:port or `ecr:[account]`. If not specified, no registry
        login is done.

    - `user`:
        Username for the registry. If registry is `ecr` type then this is ignored
        and the AWS ECR API is used to get credentials.

    - `password`:
        SSM key containing the password for the registry. If registry is `ecr`
        type then this is ignored and the AWS ECR API is used to get
        credentials.

    - `email`:
        Optional email address for registry login.

    - `server`:
        URL for the docker server. If not specified then the environment is
        used.

    - `tls`:
        Enable TLS. Boolean. Default is True.

    - `timeout`:
        Timeout on API calls in seconds.

    :param conn_id:         Connection ID. If None, then just get a default
                            connection using local environment.
    :param realm:           Realm
    :param aws_session:     A boto3 Session(). If not specified a default
                            session is created.

    :return:                A docker client.

    """

    if not conn_id:
        return docker.from_env()

    # ----------------------------------------
    # Get the connection spec and make sure its ok

    conn_spec = get_connection_spec(conn_id, realm, aws_session=aws_session)

    try:
        dict_check(conn_spec, required=DOCKER_CONNECTION_REQUIRED_FIELDS, ignore=IGNORE_FIELDS)
    except Exception as e:
        raise LavaError(f'Connection {conn_id}: {e}')

    if conn_spec['type'].lower() != 'docker':
        raise LavaError(f'Connection {conn_id}: Must be of type "docker" not {conn_spec["type"]}')

    if not conn_spec['enabled']:
        raise LavaError(f'Connection {conn_id}: Not enabled')

    # ----------------------------------------
    # Create a docker client.

    try:
        client_args = {
            'base_url': conn_spec['server'],
            'tls': conn_spec.get('tls', True),
        }
        if 'timeout' in conn_spec:
            client_args['timeout'] = int(conn_spec['timeout'])

        client = docker.DockerClient(**client_args)
    except KeyError:
        client = docker.from_env()
    except Exception as e:
        raise LavaError(f'Connection {conn_id}: {e}')

    # ----------------------------------------
    # Login to the registry

    if conn_spec.get('registry'):
        rc = get_docker_registry_credentials(conn_spec, aws_session)
        try:
            # The following just does not work so resort to docker cli
            # | response = client.login(
            # |     dockercfg_path=os.path.join(config_dir, 'config.json') if config_dir else None,
            # |     reauth=True,
            # |     **rc
            # | )
            LOG.debug(f'Logging in to docker registry {conn_spec["registry"]}')
            output = subprocess.check_output(
                [
                    'docker',
                    'login',
                    '--username',
                    rc['username'],
                    '--password-stdin',
                    rc['registry'],
                ],
                input=rc['password'],
                stderr=subprocess.STDOUT,
                text=True,
                timeout=30,
            ).strip()
            LOG.debug(f'Docker daemon login to {rc["registry"]}: {output}')
        except subprocess.CalledProcessError as e:
            raise LavaError(f'Connection {conn_id}: Cannot login to registry: {e.output}')

    return client
