"""
Lava SQL Server (mssql) connector.

This relies on FreeTDS being set up correctly in /etc/odbcinst.ini

Use one of the following to access these:

*   `lava.connection.get_pysql_connection()`
*   `lava.connection.get_cli_connection()`

"""

from __future__ import annotations

import os
from contextlib import suppress
from stat import S_IRUSR, S_IWUSR, S_IXUSR
from tempfile import mkdtemp
from typing import Any

import boto3

# Stub out pyodbc in case its not installed. Trying to use it in this case
# will cause an exception.
try:
    # noinspection PyPackageRequirements
    import pyodbc
except ImportError:
    import lava.lib.dbnone as pyodbc

from .core import LOG, cli_connector, pysql_connector

__author__ = 'Murray Andrews'

# This must link to an entry in /etc/odbcinst.ini
ODBC_DRIVER = 'FreeTDS'


# ------------------------------------------------------------------------------
@pysql_connector(dialect='mssql', subtype='pyodbc')
def py_connect_mssql(
    conn_spec: dict[str, Any], autocommit: bool = False, application_name: str = None
) -> pyodbc.Connection:
    """
    Get a connection to the specified MS SQL database.

    :param conn_spec:       Pre-expanded connection specification
    :param autocommit:      If True, attempt to enable autocommit. This is
                            database and driver dependent as not all DBs
                            support it (e.g. sqlite3) If False, autocommit is
                            not enabled (the default state for DBAPI 2.0).
    :param application_name: Application name when connecting.

    :return:                A live DB connection

    """

    db_connect_params = {
        'driver': conn_spec.get('driver', ODBC_DRIVER),
        'user': conn_spec['user'],  # AKA uid
        'password': conn_spec['password'],  # AKA pwd
        'host': conn_spec['host'],  # AKA server
        'port': conn_spec['port'],
        'database': conn_spec['database'],
    }

    if application_name:
        db_connect_params['app'] = application_name

    with suppress(KeyError):
        db_connect_params['timeout'] = int(conn_spec['timeout'])

    # This DOES NOT work. I think it could be an SSL version issue
    # | if conn_spec.get('ssl', False):
    # |     db_connect_params['encryption'] = True

    return pyodbc.connect(**db_connect_params, autocommit=autocommit)


# ------------------------------------------------------------------------------
# noinspection PyUnusedLocal
@cli_connector('mssql')
def cli_connect_mssql(
    conn_spec: dict[str, Any], workdir: str, aws_session: boto3.Session = None
) -> str:
    """
    CLI command for MS SQL.

    This just uses the lava-sql utility rather than a native SQL Server CLI as
    they are all rubbish.

    :param conn_spec:       Un-expanded connection specification
    :param workdir:         Working directory name.
    :param aws_session:     A boto3 Session().

    :return:                Name of an executable that implements the connection.

    """

    conn_dir = mkdtemp(dir=workdir, prefix='conn.')

    conn_script = (
        '#!/bin/bash\n\nlava-sql'
        f' --profile \'{aws_session.profile_name}\''
        f' --conn-id \'{conn_spec["conn_id"]}\' "$@"'
    )
    LOG.debug('MsSql script is \n%s', conn_script)

    conn_cmd_file = os.path.join(conn_dir, 'mysql')
    with open(conn_cmd_file, 'w') as fp:
        print(conn_script, file=fp)
    os.chmod(conn_cmd_file, S_IRUSR | S_IWUSR | S_IXUSR)

    return conn_cmd_file
