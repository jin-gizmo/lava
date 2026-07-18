"""
Lava MySQL family connectors.

Use one of the following to access these:

*   `lava.connection.get_cli_connection()`

*   `lava.connection.get_pysql_connection()`

"""

from __future__ import annotations

import os
import shlex
from functools import lru_cache
from stat import S_IRUSR, S_IWUSR, S_IXUSR
from subprocess import run
from tempfile import mkdtemp
from threading import Lock
from typing import Any

import boto3
import pymysql

from lava.exceptions import LavaError
from lava.lib.fileops import materialise_file
from lava.lib.ssl import build_ssl_context, resolve_ssl_mode
from .core import LOG, cli_connector, expand_sql_conn_spec, pysql_connector

__author__ = 'Murray Andrews'

MYSQL_CLI = 'mysql'


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

    if not conn_spec.get('database'):
        raise LavaError('database must be specified for MySQL')

    ssl_mode = resolve_ssl_mode(**conn_spec)
    ssl_ca_file = conn_spec.get('ssl_ca_file') or conn_spec.get('ca_cert')

    db_connect_params = {
        'user': conn_spec['user'],
        'password': conn_spec['password'],
        'host': conn_spec['host'],
        'port': conn_spec['port'],
        'database': conn_spec['database'],
        'program_name': application_name or None,
    }

    if ssl_mode:
        db_connect_params['ssl'] = build_ssl_context(ssl_mode, ssl_ca_file)

    return pymysql.connect(**db_connect_params, autocommit=autocommit)


# ------------------------------------------------------------------------------
# MySQL clients come in a couple of very similar but not identical variants,
# the MySQL (Oracle / Community Edition) one and the MariaDB one. They differ in
# some critical CLI parameters (e.g. SSL handling).
_MYSQL_NONE = 0
_MYSQL_MARIADB = 1
_MYSQL_MYSQL = 2
_mysql_version_check_lock = Lock()


# Map from lava mode names to MySQL community edition modes.
_MYSQL_CLI_SSL_MODE_MAP = {
    'require': 'REQUIRED',
    'verify-ca': 'VERIFY_CA',
    'verify-full': 'VERIFY_IDENTITY',
}


@lru_cache(maxsize=1)
def _mysql_flavour() -> int:
    """
    Determine the flavour of mysql CLI available.

    :return:        The flavour flag. See the _MYSQL_* vars
    """

    with _mysql_version_check_lock:
        cmd = [*shlex.split(MYSQL_CLI), '--version']
        try:
            result = run(cmd, capture_output=True, encoding='utf-8', check=True)
        except Exception as e:
            LOG.warning(f'No mysql CLI: {e}', extra={'event_type': 'connection'})
            return _MYSQL_NONE

        if 'mariadb' in result.stdout.lower():
            LOG.debug('mysql is MariaDB variant')
            return _MYSQL_MARIADB

        LOG.debug('mysql is MySQL (Oracle) variant')
        return _MYSQL_MYSQL


# ------------------------------------------------------------------------------
def _mysql_cli_params(
    conn_spec: dict[str, Any], ssl_mode: str | None, ssl_ca_file: str | None, conf_file: str
) -> list[str]:
    """
    Build MySQL (Oracle Community Edition) CLI parameter list.

    :param conn_spec:   Pre-expanded connection specification.
    :param ssl_mode:    Normalised SSL mode string, or None.
    :param ssl_ca_file: Local path to CA cert file, or None.
    :param conf_file:   Path to the .mysql.conf file.
    :return:            List of CLI arguments.
    """
    params = [
        f'--defaults-file={shlex.quote(conf_file)}',
        '--batch',
        '--connect-timeout=10',
    ]
    for k in ('host', 'port', 'database'):
        params.append(f'--{k}={shlex.quote(str(conn_spec[k]))}')

    if ssl_mode:
        params.append(f'--ssl-mode={_MYSQL_CLI_SSL_MODE_MAP[ssl_mode]}')
        if ssl_ca_file:
            params.append(f'--ssl-ca={shlex.quote(ssl_ca_file)}')

    if 'X-Amz-Credential=' in conn_spec['password']:
        LOG.debug('AWS IAM auth')
        if not ssl_mode:
            raise LavaError('SSL is required with IAM database authentication')
        params.append('--enable-cleartext-plugin')

    return params


def _mariadb_cli_params(
    conn_spec: dict[str, Any], ssl_mode: str | None, ssl_ca_file: str | None, conf_file: str
) -> list[str]:
    """
    Build MariaDB CLI parameter list.

    ... warning
        The MariaDB `mysql` CLI cannot properly handle the `verify-ca` mode. If
        no certificate is provided, it will effectively drop back to `require`
        mode. To force a valid certificate to be provided (either explicitly via
        a certificate file or implicitly via a publicly signed host
        certificate), `verify-full` mode is required. This will also enforce
        host name matching, which may not be what is desired.

    :param conn_spec:   Pre-expanded connection specification.
    :param ssl_mode:    Normalised SSL mode string, or None.
    :param ssl_ca_file: Local path to CA cert file, or None.
    :param conf_file:   Path to the .mysql.conf file.
    :return:            List of CLI arguments.
    """
    params = [
        f'--defaults-file={shlex.quote(conf_file)}',
        '--batch',
        '--connect-timeout=10',
    ]
    for k in ('host', 'port', 'database'):
        params.append(f'--{k}={shlex.quote(str(conn_spec[k]))}')

    if ssl_mode:
        if ssl_ca_file:
            # --ssl is implied by --ssl-ca
            params.append(f'--ssl-ca={shlex.quote(ssl_ca_file)}')
        else:
            params.append('--ssl')
        if ssl_mode == 'verify-full':
            params.append('--ssl-verify-server-cert')

    if 'X-Amz-Credential=' in conn_spec['password']:
        LOG.debug('AWS IAM auth')
        if not ssl_mode:
            raise LavaError('SSL is required with IAM database authentication')
        # --enable-cleartext-plugin not needed for MariaDB client

    return params


_cli_params_builder = {
    _MYSQL_MYSQL: _mysql_cli_params,
    _MYSQL_MARIADB: _mariadb_cli_params,
}


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
    if not conn_spec.get('database'):
        raise LavaError('database must be specified for MySQL')

    conn_dir = mkdtemp(dir=workdir, prefix='conn.')

    ssl_mode = resolve_ssl_mode(**conn_spec)
    ssl_ca_file = conn_spec.get('ssl_ca_file') or conn_spec.get('ca_cert')
    if ssl_ca_file:
        ssl_ca_file = materialise_file(ssl_ca_file, dir=conn_dir, suffix='.pem')

    # ----------------------------------------
    # Construct .mysql.conf file to automate authentication
    conf_file = os.path.join(conn_dir, '.mysql.conf')
    with open(conf_file, 'w') as fp:
        print('[client]\nuser={user}\npassword={password}'.format(**conn_spec), file=fp)
    os.chmod(conf_file, S_IRUSR | S_IWUSR)
    LOG.debug(f'Created {conf_file}')

    # ----------------------------------------
    # Build flavour-specific parameter list and construct the script
    mysql_arg_list = _cli_params_builder[mysql_flavour](conn_spec, ssl_mode, ssl_ca_file, conf_file)

    conn_script = f'#!/bin/bash\n\n{MYSQL_CLI} {" ".join(mysql_arg_list)} "$@"'

    LOG.debug(f'MYSQL script is:\n{conn_script}')

    conn_cmd_file = os.path.join(conn_dir, 'mysql')
    with open(conn_cmd_file, 'w') as fp:
        print(conn_script, file=fp)
    os.chmod(conn_cmd_file, S_IRUSR | S_IWUSR | S_IXUSR)

    return conn_cmd_file
