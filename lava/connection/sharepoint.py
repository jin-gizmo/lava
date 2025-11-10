"""Lava SharePoint connector."""

from __future__ import annotations

import os
from stat import S_IRUSR, S_IWUSR, S_IXUSR
from tempfile import mkdtemp
from typing import Any

import boto3

from lava.common import get_lava_param
from lava.config import config
from lava.lavacore import IGNORE_FIELDS, LavaError
from lava.lib.misc import dict_check, str2bool
from lava.lib.sharepoint import Sharepoint
from .core import CONNECTION_REQUIRED_FIELDS, LOG, cli_connector, get_connection_spec

__author__ = 'Murray Andrews'

SHAREPOINT_CONNECTION_REQUIRED_FIELDS = CONNECTION_REQUIRED_FIELDS | {
    'site_name',
    'tenant',
    'client_id',
    'client_secret',
    'user',
    'password',
}


# ------------------------------------------------------------------------------
def get_sharepoint_connection(
    conn_id: str, realm: str, aws_session: boto3.Session = None
) -> Sharepoint:
    """
    Get a sharepoint connection to the specified sharepoint site.

    Return a Sharepoint instance which uses a Microsoft Graph API interface.

    Connection params are (* means optional):

    - `org_base_url`:
        The organisation's SharePoint base URL.

    - `site_name`:
        The SharePoint site name.

    - `tenant`:
        Azure AD registered domain ID.

    - `client_id`:
        The Application ID that the SharePoint registration portal assigned your app.

    - `client_secret`:
        SSM key containing the client secret.

    - `user`:
        Name of the user for login to SharePoint.

    - `password`:
        SSM key containing the user's password.

    - `https_proxy`:
        HTTPS proxy to use for accessing the SharePoint API endpoints. If not
        specified the HTTPS_PROXY environment variable is used if set.

    :param conn_id:         Connection ID.
    :param realm:           Realm.
    :param aws_session:     A boto3 Session().

    :return:            A Sharepoint instance.

    """

    # ----------------------------------------
    # Get the connection spec and make sure its ok

    conn_spec = get_connection_spec(conn_id, realm, aws_session=aws_session)

    try:
        dict_check(conn_spec, required=SHAREPOINT_CONNECTION_REQUIRED_FIELDS, ignore=IGNORE_FIELDS)
    except Exception as e:
        raise LavaError(f'Connection {conn_id}: {e}')

    conn_type = conn_spec['type'].lower()

    if conn_type != 'sharepoint':
        raise LavaError(f'Connection {conn_id}: Must be of type "sharepoint" not "{conn_type}"')

    if not conn_spec['enabled']:
        raise LavaError(f'Connection {conn_id}: Not enabled')

    # Get the password from SSM.
    try:
        conn_spec['password'] = get_lava_param(conn_spec['password'], aws_session=aws_session)
    except Exception as e:
        raise LavaError(f'Connection {conn_id}: SSM {conn_spec["password"]} - {e}')

    try:
        conn_spec['client_secret'] = get_lava_param(
            conn_spec['client_secret'], aws_session=aws_session
        )
    except Exception as e:
        raise LavaError(f'Connection {conn_id}: SSM {conn_spec["client_secret"]} - {e}')

    LOG.debug(f'Connecting to sharepoint {conn_id} ({conn_type})')

    sp_connect_params = {
        'org_base_url': conn_spec['org_base_url'],
        'site_name': conn_spec['site_name'],
        'tenant': conn_spec['tenant'],
        'client_id': conn_spec['client_id'],
        'client_secret': conn_spec['client_secret'],
        'user': conn_spec['user'],
        'password': conn_spec['password'],
        'logger': LOG if config('SP_LOGGING', str2bool) else None,
    }

    if 'https_proxy' in conn_spec:
        sp_connect_params['https_proxy'] = conn_spec['https_proxy']

    try:
        conn = Sharepoint(**sp_connect_params)
    except Exception as e:
        raise LavaError(f'Connection {conn_id}: {e}')

    LOG.debug(f'Connected to sharepoint {conn_id}')

    return conn


# ------------------------------------------------------------------------------
@cli_connector('sharepoint')
def cli_connect_sharepoint(
    conn_spec: dict[str, Any], workdir: str, aws_session: boto3.Session = None
) -> str:
    """
    Generate a CLI command that will invoke lava-sharepoint.

    :param conn_spec:       Connection specification
    :param workdir:         Working directory name.
    :param aws_session:     A boto3 Session(). Not used.

    :type conn_spec:        dict[str, T]
    :type workdir:          str
    :type aws_session:      boto3.Session

    :return:                Name of an executable that implements the connection.
    :rtype:                 str
    """

    try:
        dict_check(conn_spec, required=SHAREPOINT_CONNECTION_REQUIRED_FIELDS, ignore=IGNORE_FIELDS)
    except Exception as e:
        raise LavaError(f'Connection {conn_spec.get("conn_id")}: {e}')

    conn_id = conn_spec['conn_id']
    if not aws_session:
        aws_session = boto3.Session()

    # ----------------------------------------
    # Create a little shell script that implements the connection.

    conn_script = f"""#!/bin/bash
lava-sharepoint --profile "{aws_session.profile_name}" \
--conn-id "{conn_id}" --realm "$LAVA_REALM" "$@"
    """

    LOG.debug(f'SharePoint script is {conn_script}')

    conn_cmd_file = os.path.join(mkdtemp(dir=workdir, prefix='conn.'), 'lava-sharepoint')
    with open(conn_cmd_file, 'w') as fp:
        print(conn_script, file=fp)
    os.chmod(conn_cmd_file, S_IRUSR | S_IWUSR | S_IXUSR)

    return conn_cmd_file
