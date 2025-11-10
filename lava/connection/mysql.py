"""
Lava MySQL family connectors.

Use one of the following to access these:

*   `lava.connection.get_cli_connection()`

*   `lava.connection.get_pysql_connection()`

"""

from __future__ import annotations

import os
from functools import lru_cache
from stat import S_IRUSR, S_IWUSR, S_IXUSR
from subprocess import run
from tempfile import mkdtemp
from threading import Lock
from typing import Any

import boto3
import pymysql

from lava.lavacore import LavaError
from .core import LOG, cli_connector, expand_sql_conn_spec, pysql_connector

__author__ = 'Murray Andrews'

MYSQL_SSL_CHECK_HOSTNAME = False  # False required with Python 2 and new RDS certs.


# ------------------------------------------------------------------------------
@pysql_connector(dialect='mysql', subtype='pymysql')
def py_connect_mysql(
    conn_spec: dict[str, Any],
    autocommit: bool = False,
    application_name: str = None,
) -> pymysql.Connection:
    """
    Get a connection to the specified MySQL (or MySQL-like) database.

    :param conn_spec:       Pre-expanded connection specification
    :type conn_spec:        dict[str, T]
    :param autocommit:      If True, attempt to enable autocommit. This is
                            database and driver dependent as not all DBs
                            support it (e.g. sqlite3) If False, autocommit is
                            not enabled (the default state for DBAPI 2.0).
    :param application_name: Application name when connecting.

    :return:                A live DB connection

    """

    db_connect_params = {
        'user': conn_spec['user'],
        'password': conn_spec['password'],
        'host': conn_spec['host'],
        'port': conn_spec['port'],
        'database': conn_spec['database'],
        'ssl': conn_spec.get('ssl', False),
        'program_name': application_name or None,
    }

    if conn_spec.get('ssl', False):
        db_connect_params['ssl'] = {
            'ca': conn_spec.get('ca_cert'),
            'check_hostname': MYSQL_SSL_CHECK_HOSTNAME,
        }

    return pymysql.connect(**db_connect_params, autocommit=autocommit)


# ------------------------------------------------------------------------------
# MySQL clients come in a couple of very similar but not identical variants,
# the MySQL (Oracle / Community Edition) one and the MariaDB one. They differ in
# some critical CLI parameters (e.g. SSL handling).
_MYSQL_NONE = 0
_MYSQL_MARIADB = 1
_MYSQL_MYSQL = 2
_mysql_version_check_lock = Lock()


@lru_cache(maxsize=1)
def _mysql_flavour() -> int:
    """
    Determine the flavour of mysql CLI available.

    :return:        The flavour flag. See the _MYSQL_* vars
    """

    with _mysql_version_check_lock:
        try:
            result = run(['mysql', '--version'], capture_output=True, encoding='utf-8', check=True)
        except Exception as e:
            LOG.warning(f'No mysql CLI: {e}', extra={'event_type': 'connection'})
            return _MYSQL_NONE

        if 'mariadb' in result.stdout.lower():
            LOG.debug('mysql is MariaDB variant')
            return _MYSQL_MARIADB

        LOG.debug('mysql is MySQL variant')
        return _MYSQL_MYSQL


# ------------------------------------------------------------------------------
@cli_connector('mysql', 'mariadb', 'mysql-aurora', 'mysql-rds', 'mariadb-rds')
def cli_connect_mysql(
    conn_spec: dict[str, Any], workdir: str, aws_session: boto3.Session = None
) -> str:
    """
    Generate a CLI command that will run a MySQL script.

    Requires mysql to be installed and in the PATH.

    :param conn_spec:       Un-expanded connection specification
    :param workdir:         Working directory name.
    :param aws_session:     A boto3 Session().

    :return:                Name of an executable that implements the connection.

    """

    mysql_flavour = _mysql_flavour()
    if mysql_flavour == _MYSQL_NONE:
        raise LavaError('No mysql client available')

    try:
        expand_sql_conn_spec(conn_spec, aws_session=aws_session)
    except Exception as e:
        raise LavaError(f'Connection {conn_spec.get("conn_id")}: {e}')

    # ----------------------------------------
    # Construct .mysql.conf file to automate authentication
    conn_dir = mkdtemp(dir=workdir, prefix='conn.')
    conf_file = os.path.join(conn_dir, '.mysql.conf')
    with open(conf_file, 'w') as fp:
        print('[client]\nuser={user}\npassword={password}'.format(**conn_spec), file=fp)
    os.chmod(conf_file, S_IRUSR | S_IWUSR)
    LOG.debug(f'Created {conf_file}')

    # ----------------------------------------
    # Create a little shell script that implements the connection.
    mysql_arg_list = [
        '--defaults-file="{conf_file}"',
        '--batch',
        '--host="{host}"',
        '--port={port}',
        '--connect-timeout=10',
    ]
    if 'database' in conn_spec:
        mysql_arg_list.append('--database="{database}"')

    if conn_spec.get('ssl', False):
        if mysql_flavour == _MYSQL_MYSQL:
            mysql_arg_list.append('--ssl-mode=required')
        elif mysql_flavour == _MYSQL_MARIADB:
            mysql_arg_list.append('--ssl')
        else:
            raise Exception('Internal error - unknown mysql version')

    if 'ca_cert' in conn_spec:
        mysql_arg_list.append('--ssl-ca={ca_cert}')
    if 'X-Amz-Credential=' in conn_spec['password']:
        LOG.debug('AWS IAM auth')
        if not conn_spec.get('ssl', False):
            raise LavaError('SSL is required with IAM database authentication')
        if mysql_flavour == _MYSQL_MYSQL:
            # MariaDB client doesn't need this.
            mysql_arg_list.append('--enable-cleartext-plugin')

    conn_script = '#!/bin/bash\n\nmysql {args} "$@"'.format(
        args=' '.join(mysql_arg_list).format(conf_file=conf_file, **conn_spec)
    )

    LOG.debug(f'MYSQL script is {conn_script}')

    conn_cmd_file = os.path.join(conn_dir, 'mysql')
    with open(conn_cmd_file, 'w') as fp:
        print(conn_script, file=fp)
    os.chmod(conn_cmd_file, S_IRUSR | S_IWUSR | S_IXUSR)

    return conn_cmd_file
