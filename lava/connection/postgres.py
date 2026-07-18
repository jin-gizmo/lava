"""
Lava Postgres family connectors.

Use one of the following to access these:

*   `lava.connection.get_cli_connection()`

*   `lava.connection.get_pysql_connection()`

"""

from __future__ import annotations

import os
from contextlib import suppress
from shlex import quote
from stat import S_IRUSR, S_IWUSR, S_IXUSR
from tempfile import mkdtemp
from typing import Any

import boto3
import pg8000

from lava import LavaError
from lava.lavacore import LOG
from lava.lib.fileops import materialise_file
from lava.lib.ssl import build_ssl_context, resolve_ssl_mode
from .core import cli_connector, expand_sql_conn_spec, make_application_name, pysql_connector

# Stub out PyGreSQL in case its not installed. Trying to use it in this case
# will cause an exception. We do this because PyGreSQL is a real pain to install
# in some situations.

try:
    # noinspection PyPackageRequirements
    import pgdb
except ImportError:
    from lava.lib.dbnone import dbapi_stub

    pgdb = dbapi_stub('PyGreSQL (pgdb)')

__author__ = 'Murray Andrews'

# This is a guess but psql truncates long passwords
PSQL_CLI = 'psql'
PSQL_MAX_PASSWD_LEN = 99


# ------------------------------------------------------------------------------
@pysql_connector(dialect='postgresql', subtype='pg8000')
def py_connect_pg8000(
    conn_spec: dict[str, Any], autocommit: bool = False, application_name: str = None
) -> pg8000.Connection:
    """
    Get a pg8000 connection to the specified Postgres (or Postgres-like) database.

    :param conn_spec:       Pre-expanded connection specification
    :param autocommit:      If True, attempt to enable autocommit. This is
                            database and driver dependent as not all DBs
                            support it (e.g. sqlite3) If False, autocommit is
                            not enabled (the default state for DBAPI 2.0).
    :param application_name: Application name when connecting.

    :return:                A live DB connection

    """

    if not conn_spec.get('database'):
        raise LavaError('database must be specified for Postgres')

    ssl_mode = resolve_ssl_mode(**conn_spec)
    ssl_ca_file = conn_spec.get('ssl_ca_file') or conn_spec.get('ca_cert')
    ssl_context = build_ssl_context(ssl_mode, ssl_ca_file) if ssl_mode else None

    db_connect_params = {
        'user': conn_spec['user'],
        'password': conn_spec['password'],
        'host': conn_spec['host'],
        'port': conn_spec['port'],
        'database': conn_spec['database'],
        'ssl_context': ssl_context,
        'application_name': application_name or None,
    }

    conn = pg8000.connect(**db_connect_params)
    conn.autocommit = autocommit
    return conn


# ------------------------------------------------------------------------------
@pysql_connector(dialect='postgresql', subtype='pygresql')
def py_connect_pygresql(
    conn_spec: dict[str, Any], autocommit: bool = False, application_name: str = None
) -> pgdb.Connection:
    """
    Get a pygresql connection to the specified Postgres (or Postgres-like) database.

    :param conn_spec:       Pre-expanded connection specification
    :param autocommit:      If True, attempt to enable autocommit. This is
                            database and driver dependent as not all DBs
                            support it (e.g. sqlite3) If False, autocommit is
                            not enabled (the default state for DBAPI 2.0).
    :param application_name: Application name when connecting.

    :return:                A live DB connection

    """

    if not conn_spec.get('database'):
        raise LavaError('database must be specified for Postgres')

    db_connect_params = {
        'user': conn_spec['user'],
        'password': conn_spec['password'],
        'host': conn_spec['host'],
        'port': conn_spec['port'],
        'database': conn_spec['database'],
    }

    if application_name:
        # If we include this in the connect params with a null value, pygresql
        # will actually include it with the string "None", unlike pg8000.
        # How's that for bonkers?
        db_connect_params['application_name'] = application_name

    ssl_mode = resolve_ssl_mode(**conn_spec)
    if ssl_mode:
        db_connect_params['sslmode'] = ssl_mode
        ssl_ca_file = conn_spec.get('ssl_ca_file') or conn_spec.get('ca_cert')
        cert_path = None
        if ssl_ca_file:
            try:
                cert_path = materialise_file(ssl_ca_file, suffix='.pem')
                db_connect_params['sslrootcert'] = cert_path
                conn = pgdb.connect(**db_connect_params)
            finally:
                if cert_path:
                    with suppress(FileNotFoundError):
                        os.unlink(cert_path)
            conn.autocommit = autocommit
            return conn

    conn = pgdb.connect(**db_connect_params)
    conn.autocommit = autocommit
    return conn


# ------------------------------------------------------------------------------
@cli_connector(
    'psql', 'postgres', 'postgres-aurora', 'postgres-rds', 'redshift', 'redshift-serverless'
)
def cli_connect_postgres(
    conn_spec: dict[str, Any], workdir: str, aws_session: boto3.Session = None
) -> str:
    """
    Generate a CLI command that will run a Postgres script.

    Requires psql to be installed and in the PATH.

    :param conn_spec:       Un-expanded connection specification
    :param workdir:         Working directory name.
    :param aws_session:     A boto3 Session().

    :return:                Name of an executable that implements the connection.

    """

    try:
        expand_sql_conn_spec(conn_spec, aws_session=aws_session)
    except Exception as e:
        raise LavaError(f'Connection {conn_spec.get("conn_id")}: {e}')
    if not conn_spec.get('database'):
        raise LavaError('database must be specified for Postgres')

    conn_id = conn_spec['conn_id']
    conn_dir = mkdtemp(dir=workdir, prefix='conn.')

    psql_cli_env = {
        'PGUSER': conn_spec['user'],
        'PGHOST': conn_spec['host'],
        'PGPORT': conn_spec['port'],
        'PGDATABASE': conn_spec['database'],
        'PGSSLMODE': resolve_ssl_mode(**conn_spec) or 'prefer',
    }

    ssl_ca_file = conn_spec.get('ssl_ca_file') or conn_spec.get('ca_cert')
    if ssl_ca_file:
        psql_cli_env['PGSSLROOTCERT'] = materialise_file(ssl_ca_file, dir=conn_dir, suffix='.pem')

    # PGAPPNAME allows psql to set the application_name when connecting. When
    # the script we are constructing below is called from an sqlc job, the job
    # itself will set the PGAPPNAME var and we're fine. When the script is called
    # from an exe/pkg job, it won't be set by the job so we need to make some
    # sort of fallback provision in our little connector script.
    psql_cli_env['PGAPPNAME'] = make_application_name(conn_id=conn_id)
    dynamic_appname = make_application_name(
        conn_id=conn_id, realm='${LAVA_REALM}', job_id='${LAVA_JOB_ID}'
    )

    # ------------------------------
    # Setup password auth.
    if len(conn_spec['password']) < PSQL_MAX_PASSWD_LEN:
        # Construct pgpass file to automate authentication
        conn_params = {
            k: v
            for k, v in conn_spec.items()
            if k in ('host', 'port', 'database', 'user', 'password')
        }
        for f in ('user', 'password'):
            # noinspection PyTypeChecker
            conn_params[f] = conn_params[f].replace(':', r'\:')

        pgpass_file = os.path.join(conn_dir, '.pgpass')
        with open(pgpass_file, 'w') as fp:
            print('{host}:{port}:{database}:{user}:{password}'.format(**conn_params), file=fp)
        os.chmod(pgpass_file, S_IRUSR | S_IWUSR)
        LOG.debug('Created %s', pgpass_file)
        psql_cli_env['PGPASSFILE'] = pgpass_file
    else:
        # Need to put password in the environment :-(
        LOG.debug('Password is too long for pgpass -- adding to environment instead')
        psql_cli_env['PGPASSWORD'] = conn_spec['password']

    # ------------------------------
    # Build the script file
    conn_cmd_file = os.path.join(conn_dir, 'psql')
    psql_args = (
        f'{PSQL_CLI} --no-psqlrc --quiet --no-password --set ON_ERROR_STOP=on --pset footer=off'
    )
    with open(conn_cmd_file, 'w') as fp:
        print('#!/bin/bash', file=fp)
        for k, v in psql_cli_env.items():
            if v:
                print(f'export {k}={quote(str(v))}', file=fp)
        # PGAPPNAME is special because script user can override it and it can be
        # constucted dynamically. We need shell var expansion in the dynanmic name.
        print(f'[ "$PGAPPNAME" == "" ] && PGAPPNAME="{dynamic_appname}"', file=fp)
        print(f'{psql_args} "$@"', file=fp)
    os.chmod(conn_cmd_file, S_IRUSR | S_IWUSR | S_IXUSR)

    return conn_cmd_file
