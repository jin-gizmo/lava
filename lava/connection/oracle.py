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
from typing import Any, Literal

import boto3
import oracledb

from lava import LavaError
from lava.config import config
from lava.lib.ssl import build_ssl_context, resolve_ssl_mode
from lava.version import __version__
from .core import LOG, cli_connector, expand_sql_conn_spec, pysql_connector

__author__ = 'Murray Andrews'

ORACLE_CLIENT_ID_LEN = 64
ORACLE_CLIENT_INFO_LEN = 64
ORACLE_MODULE_LEN = 48
ORACLE_CLI = 'sqlplus'

# Only allowed to do this once!
if config('ORACLE_CONNECTION_MODE') == 'thick':
    LOG.debug('Setting ORACLE_CONNECTION_MODE to thick')
    oracledb.init_oracle_client(lib_dir=config('ORACLE_LIB_DIR') or None)
    LOG.debug('Oracle Connection is_thin_mode=%s', oracledb.is_thin_mode())


# ------------------------------------------------------------------------------
def marshal_ssl_params(
    ssl_mode: str, ssl_ca_file: str | None = None, mode: Literal['thin', 'thick'] = 'thin'
) -> dict[str, Any]:
    """
    Build the SSL-related keyword arguments for oracledb.connect().

    Handles the thin/thick mode split and constructs the appropriate
    combination of ssl_context and ssl_server_dn_match parameters.

    :param ssl_mode:    SSL mode string ('require', 'verify-ca', or 'verify-full').
    :param ssl_ca_file: CA certificate file path or URI, or None.
    :param mode:        The OracleDB connection mode: 'thin' or 'thick'.

    :returns:           Dict of SSL keyword arguments for oracledb.connect().
    :raises LavaError:  If thick mode is used with any SSL configuration,
                        or if ssl_ca_file is specified in thick mode.
    """

    if mode == 'thin':
        ctx = build_ssl_context(ssl_mode, ssl_ca_file)
        return {
            'ssl_context': ctx,
            # Oracledb uses this rather than the SSLContext for hostname checking.
            'ssl_server_dn_match': ctx.check_hostname,
        }

    if mode != 'thick':
        raise ValueError(f'Bad Oracle connection mode: {mode}')

    # Thick mode: ssl_context is not used. The C library performs its own TLS.
    # ssl_mode=require is not achievable and ssl_ca_file can't be supplied
    # without Oracle Wallet.
    if ssl_mode == 'require':
        raise LavaError('ssl_mode=require is not supported for the oracle connector in thick mode')
    if ssl_ca_file:
        raise LavaError('ssl_ca_file is not supported for the oracle connector in thick mode')

    # verify-ca and verify-full: believed supported via ssl_server_dn_match.
    LOG.warning(
        'Oracle thick mode SSL (ssl_mode=%s): '
        'Certificate validation is performed by the Oracle C client library. '
        'This configuration is untested — a publicly-trusted server '
        'certificate is required.',
        ssl_mode,
    )
    # ssl_context not used in thick mode.
    return {'ssl_server_dn_match': ssl_mode == 'verify-full'}


# ------------------------------------------------------------------------------
def marshal_connect_params(
    conn_spec: dict[str, Any], mode: Literal['thin', 'thick'] = 'thin'
) -> dict[str, Any]:
    """
    Marshal oracle connection parameters.

    :param conn_spec:   Pre-expanded connection specification
    :param mode:        The OracleDB connection mode: 'thin' or 'thick'.
    :return:            Dict of SSL keyword arguments for oracledb.connect().
    """

    conn_spec['port'] = int(conn_spec['port'])

    ssl_mode = resolve_ssl_mode(**conn_spec)
    ssl_ca_file = conn_spec.get('ssl_ca_file') or conn_spec.get('ca_cert')
    ssl_params = marshal_ssl_params(ssl_mode, ssl_ca_file, mode) if ssl_mode else {}

    db_connect_params = {
        'user': '...',  # Update after debug logging
        'password': '...',  # Update after debug logging
        'host': conn_spec['host'],
        'port': conn_spec['port'],
        'service_name': conn_spec.get('service_name'),
        'sid': conn_spec.get('sid', conn_spec.get('database')),
        'protocol': 'tcps' if ssl_mode else 'tcp',
        **ssl_params,
    }
    with suppress(KeyError):
        db_connect_params['edition'] = conn_spec['edition']
    LOG.debug('Oracle connection params: %s', db_connect_params)
    return db_connect_params | {'user': conn_spec['user'], 'password': conn_spec['password']}


# ------------------------------------------------------------------------------
# noinspection PyUnusedLocal
@pysql_connector(dialect='oracle', subtype='oracledb')
def py_connect_oracledb(
    conn_spec: dict[str, Any],
    autocommit: bool = False,
    application_name: str = None,
) -> oracledb.Connection:
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

    db_connect_params = marshal_connect_params(
        conn_spec, mode='thin' if oracledb.is_thin_mode() else 'thick'
    )
    conn = oracledb.connect(**db_connect_params)
    conn.autocommit = autocommit
    if application_name:
        conn.client_identifier = application_name[0:ORACLE_CLIENT_ID_LEN]
    conn.module = 'lava'[:ORACLE_MODULE_LEN]
    conn.clientinfo = f'lava v{__version__} / {oracledb.__name__} v{oracledb.__version__}'[
        :ORACLE_CLIENT_INFO_LEN
    ]
    return conn


# ------------------------------------------------------------------------------
# noinspection PyUnusedLocal
@pysql_connector(dialect='oracle', subtype='cx_oracle')
def py_connect_cx_oracle(
    conn_spec: dict[str, Any],
    autocommit: bool = False,
    application_name: str = None,
) -> oracledb.Connection:
    """
    Get a connection to the specified Oracle database.

    !!! warning "Deprecated"
        This is now just an alias for subtype=`oracledb`.

    :param conn_spec:       Pre-expanded connection specification
    :param autocommit:      If True, attempt to enable autocommit. This is
                            database and driver dependent as not all DBs
                            support it (e.g. sqlite3) If False, autocommit is
                            not enabled (the default state for DBAPI 2.0).
    :param application_name: Not used.

    :return:                A live DB connection.

    """
    LOG.warning(
        (
            'Deprecation warning: The cx_oracle subtype for the Oracle connector is'
            ' now just an alias for the default "oracledb" subtype.'
        ),
        extra={'event_type': 'connection'},
    )

    return py_connect_oracledb(conn_spec, autocommit=autocommit, application_name=application_name)


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
        raise LavaError(f'Connection {conn_spec.get("conn_id")}: {e}') from e

    conn_id = conn_spec['conn_id']

    try:
        db_connect_params = marshal_connect_params(conn_spec, mode='thick')
    except Exception as e:
        raise LavaError(f'Connection {conn_id}: {e}') from e

    dsn = oracledb.ConnectParams(**db_connect_params).get_connect_string()
    LOG.debug(f'Oracle DSN: {dsn}')

    try:
        compatibility = '-C ' + str(conn_spec['edition'])
    except KeyError:
        compatibility = ''

    # ----------------------------------------
    # Create a little shell script that implements the connection.

    # SECURITY WARNING: Password will be visible to ps listing but no option with sqlplus.
    conn_script = """#!/bin/bash
{cli} -NOLOGINTIME -L -S {compatibility} '{user}/{password}@{dsn}' "$@"
    """.format(cli=ORACLE_CLI, dsn=dsn, compatibility=compatibility, **conn_spec)

    conn_cmd_file = os.path.join(mkdtemp(dir=workdir, prefix='conn.'), 'sqlplus')
    with open(conn_cmd_file, 'w') as fp:
        print(conn_script, file=fp)
    os.chmod(conn_cmd_file, S_IRUSR | S_IWUSR | S_IXUSR)

    return conn_cmd_file
