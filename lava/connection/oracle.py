"""
Lava Oracle connector.

Use one of the following to access these:

*   `lava.connection.get_cli_connection()`

*   `lava.connection.get_pysql_connection()`

"""

from __future__ import annotations

import os
from contextlib import suppress
from stat import S_IRUSR, S_IWUSR, S_IXUSR
from tempfile import mkdtemp
from typing import Any

import boto3
import cx_Oracle

from lava.lavacore import LavaError
from lava.lib.misc import dict_strip
from .core import LOG, cli_connector, expand_sql_conn_spec, pysql_connector

__author__ = 'Murray Andrews'


# ------------------------------------------------------------------------------
# noinspection PyUnusedLocal
@pysql_connector(dialect='oracle', subtype='cx_oracle')
def py_connect_oracle(
    conn_spec: dict[str, Any],
    autocommit: bool = False,
    application_name: str = None,
) -> cx_Oracle.Connection:
    """
    Get a connection to the specified Oracle database.

    :param conn_spec:       Pre-expanded connection specification
    :param autocommit:      If True, attempt to enable autocommit. This is
                            database and driver dependent as not all DBs
                            support it (e.g. sqlite3) If False, autocommit is
                            not enabled (the default state for DBAPI 2.0).
    :param application_name: Not used.

    :return:                A live DB connection.

    """

    conn_id = conn_spec['conn_id']

    try:
        conn_spec['port'] = int(conn_spec['port'])
    except ValueError:
        raise LavaError(f'Connection {conn_id}: Bad port {conn_spec["port"]}')

    dsn = cx_Oracle.makedsn(
        **dict_strip(
            {
                'host': conn_spec['host'],
                'port': conn_spec['port'],
                'service_name': conn_spec.get('service_name'),
                'sid': conn_spec.get('sid', conn_spec.get('database')),
            }
        )
    )

    LOG.debug(f'Oracle DSN: {dsn}')

    db_connect_params = {'user': conn_spec['user'], 'password': conn_spec['password'], 'dsn': dsn}
    with suppress(KeyError):
        db_connect_params['edition'] = conn_spec['edition']

    conn = cx_Oracle.connect(**db_connect_params)
    conn.autocommit = autocommit
    return conn


# ------------------------------------------------------------------------------
@cli_connector('oracle', 'oracle-rds')
def cli_connect_oracle(
    conn_spec: dict[str, Any], workdir: str, aws_session: boto3.Session = None
) -> str:
    """
    Generate a CLI command that will run an Oracle script.

    Requires sqlplus to be installed and in the PATH.

    !!! warning
        Oracle is such a klutz. There is no way to protect the password from ps
        list. Use this at your own risk.

    :param conn_spec:       Un-expanded connection specification
    :param workdir:         Working directory name.
    :param aws_session:     A boto3 Session().

    :return:                Name of an executable that implements the connection.

    """

    try:
        expand_sql_conn_spec(conn_spec, aws_session=aws_session)
    except Exception as e:
        raise LavaError(f'Connection {conn_spec.get("conn_id")}: {e}')

    # ----------------------------------------
    dsn = cx_Oracle.makedsn(
        **dict_strip(
            {
                'host': conn_spec['host'],
                'port': conn_spec['port'],
                'service_name': conn_spec.get('service_name'),
                'sid': conn_spec.get('sid', conn_spec.get('database')),
            }
        )
    )

    LOG.debug(f'Oracle DSN: {dsn}')

    try:
        compatibility = '-C ' + str(conn_spec['edition'])
    except KeyError:
        compatibility = ''

    # ----------------------------------------
    # Create a little shell script that implements the connection.

    # SECURITY WARNING: Password will be visible to ps listing but no option with sqlplus.
    conn_script = """#!/bin/bash
sqlplus -NOLOGINTIME -L -S {compatibility} '{user}/{password}@{dsn}' "$@"
    """.format(
        dsn=dsn, compatibility=compatibility, **conn_spec
    )

    conn_cmd_file = os.path.join(mkdtemp(dir=workdir, prefix='conn.'), 'sqlplus')
    with open(conn_cmd_file, 'w') as fp:
        print(conn_script, file=fp)
    os.chmod(conn_cmd_file, S_IRUSR | S_IWUSR | S_IXUSR)

    return conn_cmd_file
