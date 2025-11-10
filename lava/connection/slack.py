"""Lava Slack connector."""

from __future__ import annotations

import os
from stat import S_IRUSR, S_IWUSR, S_IXUSR
from tempfile import mkdtemp
from typing import Any

import boto3

from lava.lavacore import IGNORE_FIELDS, LavaError
from lava.lib.misc import dict_check
from lava.lib.slack import Slack
from .core import (
    CONNECTION_OPTIONAL_FIELDS,
    CONNECTION_REQUIRED_FIELDS,
    LOG,
    cli_connector,
    get_connection_spec,
)

__author__ = 'Murray Andrews'

SLACK_CONNECTION_REQUIRED_FIELDS = CONNECTION_REQUIRED_FIELDS | {'webhook_url'}
SLACK_CONNECTION_OPTIONAL_FIELDS = CONNECTION_OPTIONAL_FIELDS | {
    'from',
    'style',
    'colour',
    'preamble',
}


# ------------------------------------------------------------------------------
def get_slack_connection(conn_id: str, realm: str, aws_session: boto3.Session = None) -> Slack:
    """
    Get a connection to a Slack message sender.

    :param conn_id:         Connection ID
    :param realm:           Realm.
    :param aws_session:     A boto3 Session().

    :return:                A Slack instance.

    """

    # ----------------------------------------
    # Get the connection spec and make sure its ok

    conn_spec = get_connection_spec(conn_id, realm, aws_session=aws_session)

    try:
        dict_check(
            conn_spec,
            required=SLACK_CONNECTION_REQUIRED_FIELDS,
            optional=SLACK_CONNECTION_OPTIONAL_FIELDS,
            ignore=IGNORE_FIELDS,
        )
    except Exception as e:
        raise LavaError(f'Connection {conn_id}: {e}')

    conn_type = conn_spec['type'].lower()

    if conn_type != 'slack':
        raise LavaError(f'Connection {conn_id}: Must be of type "slack" not "{conn_type}"')

    if not conn_spec['enabled']:
        raise LavaError(f'Connection {conn_id}: Not enabled')

    return Slack(conn_spec, realm, logger=LOG)


# ------------------------------------------------------------------------------
@cli_connector('slack')
def cli_connect_slack(
    conn_spec: dict[str, Any], workdir: str, aws_session: boto3.Session = None
) -> str:
    """
    Generate a CLI command to run the `lava-slack` utility to send a Slack message.

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
        dict_check(
            conn_spec,
            required=SLACK_CONNECTION_REQUIRED_FIELDS,
            optional=SLACK_CONNECTION_OPTIONAL_FIELDS,
            ignore=IGNORE_FIELDS,
        )
    except Exception as e:
        raise LavaError(f'Connection {conn_spec.get("conn_id")}: {e}')

    conn_id = conn_spec['conn_id']
    if not aws_session:
        aws_session = boto3.Session()

    cmd = (
        f'lava-slack --profile "{aws_session.profile_name}"'
        f' --conn-id "{conn_id}" --realm "$LAVA_REALM"'
    )

    # ----------------------------------------
    # Create a little shell script that implements the connection.

    conn_script = f"""#!/bin/bash
{cmd} "$@"
    """

    LOG.debug(f'Slack script is {conn_script}')

    conn_cmd_file = os.path.join(mkdtemp(dir=workdir, prefix='conn.'), 'lava-slack')
    with open(conn_cmd_file, 'w') as fp:
        print(conn_script, file=fp)
    os.chmod(conn_cmd_file, S_IRUSR | S_IWUSR | S_IXUSR)

    return conn_cmd_file
