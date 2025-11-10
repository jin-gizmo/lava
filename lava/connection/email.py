"""Lava email connector."""

from __future__ import annotations

import os
from stat import S_IRUSR, S_IWUSR, S_IXUSR
from tempfile import mkdtemp
from typing import Any

import boto3

from lava.config import config
from lava.lavacore import IGNORE_FIELDS, LavaError
from lava.lib.email import Emailer
from lava.lib.misc import dict_check, listify
from .core import (
    CONNECTION_OPTIONAL_FIELDS,
    CONNECTION_REQUIRED_FIELDS,
    LOG,
    cli_connector,
    get_connection_spec,
)

__author__ = 'Murray Andrews'

EMAIL_CONNECTION_REQUIRED_FIELDS = CONNECTION_REQUIRED_FIELDS
EMAIL_CONNECTION_OPTIONAL_FIELDS = CONNECTION_OPTIONAL_FIELDS | {
    'from',
    'region',
    'return_path',
    'reply_to',
    'subtype',
    'user',
    'host',
    'password',
    'port',
    'tls',
    'configuration_set',
}


# ------------------------------------------------------------------------------
def get_email_connection(conn_id: str, realm: str, aws_session: boto3.Session = None) -> Emailer:
    """
    Get a connection to an email sender.

    This returns a [lava.lib.email.Emailer][lava.lib.email.Emailer] instance
    which can be used as a context manager. Otherwise it is up to the caller to
    call the handler's `close()` method.

    This provides a common interface to an email sending subsystem, independent
    of the underlying sending mechanism. Different sending mechanisms can be
    selected using the `subtype` field in the connection spec. The default
    handler is AWS SES.

    Typical usage would be:

    ```python
    with get_email_connection('my_conn_id', 'realm-name') as emailer:
        emailer.send(to='x@y.com', subject='Hello', message='world')
    ```

    :param conn_id:         Connection ID
    :param realm:           Realm.
    :param aws_session:     A boto3 Session().

    :return:                An Emailer instance.

    """

    # ----------------------------------------
    # Get the connection spec and make sure its ok

    conn_spec = get_connection_spec(conn_id, realm, aws_session=aws_session)

    try:
        dict_check(
            conn_spec,
            required=EMAIL_CONNECTION_REQUIRED_FIELDS,
            optional=EMAIL_CONNECTION_OPTIONAL_FIELDS,
            ignore=IGNORE_FIELDS,
        )
    except Exception as e:
        raise LavaError(f'Connection {conn_id}: {e}')

    conn_type = conn_spec['type'].lower()

    if conn_type not in ('email', 'ses'):
        raise LavaError(f'Connection {conn_id}: Must be of type "email" or "ses" not "{conn_type}"')

    if not conn_spec['enabled']:
        raise LavaError(f'Connection {conn_id}: Not enabled')

    return Emailer.handler(conn_spec, realm, aws_session=aws_session, logger=LOG)


# ------------------------------------------------------------------------------
@cli_connector('ses')
def cli_connect_ses(
    conn_spec: dict[str, Any], workdir: str, aws_session: boto3.Session = None
) -> str:
    """
    Generate a CLI command that will invoke AWS SES to send an email.

    !!! warning "Deprecated"
        Use the cli_connect_email() connector instead.

    :param conn_spec:       Connection specification
    :param workdir:         Working directory name.
    :param aws_session:     A boto3 Session(). Not used.

    :return:                Name of an executable that implements the connection.

    """

    LOG.warning(
        'Deprecation warning: The ses connector will be removed in a future release',
        extra={'event_type': 'connection'},
    )
    try:
        dict_check(
            conn_spec,
            required=EMAIL_CONNECTION_REQUIRED_FIELDS,
            optional=EMAIL_CONNECTION_OPTIONAL_FIELDS,
            ignore=IGNORE_FIELDS,
        )
    except Exception as e:
        raise LavaError(f'Connection {conn_spec.get("conn_id")}: {e}')

    if not aws_session:
        aws_session = boto3.Session()

    region = conn_spec.get('region', config('SES_REGION'))

    sender = conn_spec.get('from', config('SES_FROM'))
    if not sender:
        raise LavaError('No "from" for SES found')

    return_path = conn_spec.get('return_path', '')

    reply_to = conn_spec.get('reply_to', '')
    if isinstance(reply_to, list):
        reply_to = ' '.join(reply_to)

    # ----------------------------------------
    # Create a little shell script that implements the connection.

    conn_script = f"""#!/bin/bash
stdin=yes
for i
do
    case "$i"
    in
        --subject | --to | --cc | --bcc) ;;
        --html | --text) stdin=no;;
        --*) echo "Bad option: $i" >&2; exit 1;;
        *) ;;
    esac
done
z=2
trap '/bin/rm -f msg.$$; exit $z' 0
if [ "$stdin" == yes ]
then
    cat > msg.$$
    source="--text file://msg.$$"
    head -1 msg.$$ | grep -qi '^<html>' && source="--html file://msg.$$"
fi
[ "{return_path}" != "" ] && return_path='--return-path "{return_path}"'
[ "{reply_to}" != "" ] && reply_to='--reply-to-addresses {reply_to}'
aws --profile "{aws_session.profile_name}" --region "{region}" \\
    ses send-email --from "{sender}" $return_path $reply_to "$@" $source
z=0
    """

    LOG.debug(f'EMAIL script is {conn_script}')

    conn_cmd_file = os.path.join(mkdtemp(dir=workdir, prefix='conn.'), 'ses')
    with open(conn_cmd_file, 'w') as fp:
        print(conn_script, file=fp)
    os.chmod(conn_cmd_file, S_IRUSR | S_IWUSR | S_IXUSR)

    return conn_cmd_file


# ------------------------------------------------------------------------------
@cli_connector('email')
def cli_connect_email(
    conn_spec: dict[str, Any], workdir: str, aws_session: boto3.Session = None
) -> str:
    """
    Generate a CLI command to invoke the `lava-email` utility to send an email.

    :param conn_spec:       Connection specification
    :param workdir:         Working directory name.
    :param aws_session:     A boto3 Session(). Not used.

    :return:                Name of an executable that implements the connection.
    """

    try:
        dict_check(
            conn_spec,
            required=EMAIL_CONNECTION_REQUIRED_FIELDS,
            optional=EMAIL_CONNECTION_OPTIONAL_FIELDS,
            ignore=IGNORE_FIELDS,
        )
    except Exception as e:
        raise LavaError(f'Connection {conn_spec.get("conn_id")}: {e}')

    conn_id = conn_spec['conn_id']
    if not aws_session:
        aws_session = boto3.Session()

    cmd = (
        f'lava-email --profile "{aws_session.profile_name}"'
        f' --conn-id "{conn_id}" --realm "$LAVA_REALM"'
    )
    if conn_spec.get('from'):
        cmd += f' --from "{conn_spec["from"]}"'
    if conn_spec.get('reply_to'):
        cmd += ''.join([f' --reply-to "{s}"' for s in listify(conn_spec['reply_to'])])

    # ----------------------------------------
    # Create a little shell script that implements the connection.

    conn_script = f"""#!/bin/bash
{cmd} "$@"
    """

    LOG.debug(f'Email script is {conn_script}')

    conn_cmd_file = os.path.join(mkdtemp(dir=workdir, prefix='conn.'), 'lava-email')
    with open(conn_cmd_file, 'w') as fp:
        print(conn_script, file=fp)
    os.chmod(conn_cmd_file, S_IRUSR | S_IWUSR | S_IXUSR)

    return conn_cmd_file
