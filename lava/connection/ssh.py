"""
Lava SSH family connectors.

Use the following to access these:

*   `lava.connection.get_cli_connection()`

"""

from __future__ import annotations

import os
from shlex import quote
from stat import S_IRUSR, S_IWUSR, S_IXUSR
from tempfile import mkdtemp
from typing import Any

import boto3

from lava.common import get_lava_param
from lava.lavacore import IGNORE_FIELDS, LavaError
from lava.lib.misc import dict_check
from .core import CONNECTION_REQUIRED_FIELDS, LOG, cli_connector

__author__ = 'Murray Andrews'

SSH_CONNECTION_REQUIRED_FIELDS = CONNECTION_REQUIRED_FIELDS | {'ssh_key'}
GIT_CONNECTION_REQUIRED_FIELDS = SSH_CONNECTION_REQUIRED_FIELDS


# ------------------------------------------------------------------------------
def install_ssh_key(
    ssm_param_name: str, key_file_name: str, aws_session: boto3.Session = None
) -> None:
    """
    Extract an SSH key from SSM and put it in a file.

    :param ssm_param_name:  SSM parameter name containing the key. This may have
                            been joined into a single line with commas replacing
                            line breaks and will need to be unpacked before use.
    :param key_file_name:   Name of file in which to place the key.
    :param aws_session:     A boto3 Session().

    """

    if not aws_session:
        aws_session = boto3.Session()

    # Get the SSH key from KMS. This may have been joined into a single line for
    # SSM and will need to be unpacked before use.
    try:
        ssh_key = get_lava_param(ssm_param_name, aws_session=aws_session)
    except Exception as e:
        raise LavaError(f'SSM {ssm_param_name} - {e}')

    ssh_key = ssh_key.replace(',', '\n')

    # Create the file
    with open(key_file_name, 'w') as kfp:
        print(ssh_key, file=kfp)
    os.chmod(key_file_name, S_IRUSR | S_IWUSR)


# ------------------------------------------------------------------------------
@cli_connector('ssh', 'scp', 'sftp')
def cli_connect_ssh(
    conn_spec: dict[str, Any], workdir: str, aws_session: boto3.Session = None
) -> str:
    """
    Generate a CLI command to run the ssh family with lava managed SSH keys.

    :param conn_spec:       Connection specification
    :param workdir:         Working directory name.
    :param aws_session:     A boto3 Session(). This is used to get credentials.

    :return:                Name of an executable that implements the connection.

    """

    try:
        dict_check(conn_spec, required=SSH_CONNECTION_REQUIRED_FIELDS, ignore=IGNORE_FIELDS)
    except Exception as e:
        raise LavaError(f'Connection {conn_spec.get("conn_id")}: {e}')

    conn_id = conn_spec['conn_id']
    conn_type = conn_spec['type']

    # ----------------------------------------
    # Create a dedicated directory for the connection details.

    conn_dir = mkdtemp(dir=workdir, prefix='conn.')

    # ----------------------------------------
    # Install the SSH key

    key_file_name = os.path.join(conn_dir, 'ssh.pem')
    try:
        install_ssh_key(conn_spec['ssh_key'], key_file_name, aws_session=aws_session)
    except Exception as e:
        raise LavaError(f'Connection {conn_id}: {e}')

    # ----------------------------------------
    # Create a little shell script that implements the connection.

    ssh_options = conn_spec.get('ssh_options', [])
    if not isinstance(ssh_options, list):
        raise LavaError('ssh_options must be a list of strings')
    ssh_opt_s = ' '.join(f'-o {quote(opt)}' for opt in ssh_options)

    conn_script = f'#!/bin/bash\n{conn_type} {ssh_opt_s} -i {key_file_name} "$@"'

    LOG.debug(f'{conn_type} script is {conn_script}')

    conn_cmd_file = os.path.join(conn_dir, conn_type)
    with open(conn_cmd_file, 'w') as fp:
        print(conn_script, file=fp)
    os.chmod(conn_cmd_file, S_IRUSR | S_IWUSR | S_IXUSR)

    return conn_cmd_file


# ------------------------------------------------------------------------------
@cli_connector('git')
def cli_connect_git(
    conn_spec: dict[str, Any], workdir: str, aws_session: boto3.Session = None
) -> str:
    """
    Generate a CLI command to run git with lava managed SSH keys.

    :param conn_spec:       Connection specification
    :param workdir:         Working directory name.
    :param aws_session:     A boto3 Session(). This is used to get credentials.

    :return:                Name of an executable that implements the connection.

    """

    try:
        dict_check(conn_spec, required=GIT_CONNECTION_REQUIRED_FIELDS, ignore=IGNORE_FIELDS)
    except Exception as e:
        raise LavaError(f'Connection {conn_spec.get("conn_id")}: {e}')

    conn_id = conn_spec['conn_id']

    # ----------------------------------------
    # Create a dedicated directory for the connection details.

    conn_dir = mkdtemp(dir=workdir, prefix='conn.')

    # ----------------------------------------
    # Install the SSH key

    key_file_name = os.path.join(conn_dir, 'ssh.pem')
    try:
        install_ssh_key(conn_spec['ssh_key'], key_file_name, aws_session=aws_session)
    except Exception as e:
        raise LavaError(f'Connection {conn_id}: {e}')

    # ----------------------------------------
    # Create a little shell script that implements the connection.

    ssh_options = conn_spec.get('ssh_options', [])
    if not isinstance(ssh_options, list):
        raise LavaError('ssh_options must be a list of strings')
    ssh_opt_s = ' '.join(f'-o {quote(opt)}' for opt in ssh_options)

    conn_script = f"""#!/bin/bash
export GIT_CONFIG_NOSYSTEM=1
export GIT_SSH_COMMAND='ssh {ssh_opt_s} -i {key_file_name}'
export GIT_TERMINAL_PROMPT=0

git "$@"
"""

    LOG.debug(f'GIT script is {conn_script}')

    conn_cmd_file = os.path.join(conn_dir, 'git')
    with open(conn_cmd_file, 'w') as fp:
        print(conn_script, file=fp)
    os.chmod(conn_cmd_file, S_IRUSR | S_IWUSR | S_IXUSR)

    return conn_cmd_file
