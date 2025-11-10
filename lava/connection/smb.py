"""Lava SMB connector."""

from __future__ import annotations

import os
from stat import S_IRUSR, S_IWUSR, S_IXUSR
from tempfile import mkdtemp
from typing import Any

import boto3

from lava.lavacore import IGNORE_FIELDS, LavaError
from lava.lib.misc import dict_check
from lava.lib.smb import PySMBConnection, SMBProtocolConnection
from .core import (
    LOG,
    SMB_CONNECTION_OPTIONAL_FIELDS,
    SMB_CONNECTION_REQUIRED_FIELDS,
    cli_connector,
    smb_connector,
)

__author__ = 'Murray Andrews, Alex Boul'


# ------------------------------------------------------------------------------
@smb_connector('pysmb')
def smb_connect_pysmb(conn_spec: dict[str, Any]) -> PySMBConnection:
    """
    Get an SMB connection to the specified SMB fileshare using pysmb.

    It is up to the caller to close the connection.

    Allowed parameters are defined as per
    https://pysmb.readthedocs.io/en/latest/api/smb_SMBConnection.html.
    Parameters marked * are optional.

    - user
        User name for login to the remote server.

    - password
       SSM key containing the password for the server.

    - host
        Name or IP of the SMB host.

    - port
        Connection port number. If not specified, 139 is used if is_direct_tcp
        is False and 445 if is_direct_tcp is true.

    - remote_name
        NetBIOS machine name of the remote server.

    - my_name*
        Local NetBIOS machine name that will identify where this connection is
        originating from. If not specified, defaults to the first 15 characters
        of `lava-<REALM>`

    - domain*
        The network domain. Defaults to an empty string.

    - use_ntlm_v2*
        Boolean. Indicates whether pysmb should be NTLMv1 or NTLMv2
        authentication algorithm for authentication. Default is True.

    :param conn_spec:       Pre-expanded connection specification
    :return:                An active SMB connection

    """
    is_direct_tcp = conn_spec.get('is_direct_tcp', False)

    conn = PySMBConnection(
        username=conn_spec['user'],
        password=conn_spec['password'],
        my_name=conn_spec['my_name'][0:15],
        remote_name=conn_spec['remote_name'],
        domain=conn_spec.get('domain', ''),
        use_ntlm_v2=conn_spec.get('use_ntlm_v2', True),
        is_direct_tcp=is_direct_tcp,
    )

    conn.connect(
        ip=conn_spec['host'],
        port=int(conn_spec.get('port', 445 if is_direct_tcp else 139)),
    )

    return conn


# ------------------------------------------------------------------------------
@smb_connector('smbprotocol')
def smb_connect_smbprotocol(conn_spec: dict[str, Any]) -> SMBProtocolConnection:
    """
    Get an SMB connection to the specified SMB fileshare using smbprotocol.

    It is up to the caller to close the connection.

    Allowed parameters are defined as per
    https://pysmb.readthedocs.io/en/latest/api/smb_SMBConnection.html.
    Parameters marked * are optional.

    - user
        User name for login to the remote server.

    - password
       SSM key containing the password for the server.

    - host
        Name or IP of the SMB host.

    - port
        Connection port number. If not specified, 139 is used if is_direct_tcp
        is False and 445 if is_direct_tcp is true.

    - remote_name
        NetBIOS machine name of the remote server.

    - my_name*
        Local NetBIOS machine name that will identify where this connection is
        originating from. If not specified, defaults to the first 15 characters
        of `lava-<REALM`

    - domain*
        The network domain used for connecting via DFS. Defaults to an empty string.

    - use_ntlm_v2*
        Boolean. Indicates whether smbprotocol should be NTLMv1 or NTLMv2
        authentication algorithm for authentication. Default is True.

    - encrypt*
        Boolean. Indicates whether encryption should be used for all requests and
        file transfers with the connector. Default is False.

    :param conn_spec:       Pre-expanded connection specification
    :return:                An active SMB connection

    """
    is_direct_tcp = conn_spec.get('is_direct_tcp', False)

    conn = SMBProtocolConnection(
        username=conn_spec['user'],
        password=conn_spec['password'],
        my_name=conn_spec['my_name'].ljust(16),
        remote_name=conn_spec['remote_name'],
        domain=conn_spec.get('domain', ''),
        use_ntlm_v2=conn_spec.get('use_ntlm_v2', True),
        is_direct_tcp=is_direct_tcp,
        encrypt=conn_spec.get('encrypt', False),
    )

    conn.connect(
        ip=conn_spec['host'],
        port=int(conn_spec.get('port', 445 if is_direct_tcp else 139)),
    )

    return conn


# ------------------------------------------------------------------------------
@cli_connector('smb')
def cli_connect_smb(
    conn_spec: dict[str, Any], workdir: str, aws_session: boto3.Session = None
) -> str:
    """
    Generate a CLI command that will invoke lava-smb.

    :param conn_spec:       Connection specification
    :param workdir:         Working directory name.
    :param aws_session:     A boto3 Session(). Not used.

    :return:                Name of an executable that implements the connection.
    """

    try:
        dict_check(
            conn_spec,
            required=SMB_CONNECTION_REQUIRED_FIELDS,
            optional=SMB_CONNECTION_OPTIONAL_FIELDS,
            ignore=IGNORE_FIELDS,
        )
    except Exception as e:
        raise LavaError(f'Connection {conn_spec.get("conn_id")}: {e}')

    conn_id = conn_spec['conn_id']
    if not aws_session:
        aws_session = boto3.Session()

    # ----------------------------------------
    # Create a little shell script that implements the connection.

    conn_script = f"""#!/bin/bash
lava-smb --profile "{aws_session.profile_name}" --conn-id "{conn_id}" --realm "$LAVA_REALM" "$@"
    """

    LOG.debug(f'SMB script is {conn_script}')

    conn_cmd_file = os.path.join(mkdtemp(dir=workdir, prefix='conn.'), 'lava-smb')
    with open(conn_cmd_file, 'w') as fp:
        print(conn_script, file=fp)
    os.chmod(conn_cmd_file, S_IRUSR | S_IWUSR | S_IXUSR)

    return conn_cmd_file
