"""Handle Redshift specifics."""

from __future__ import annotations

from typing import Any

import boto3
import pg8000

from lava.config import config
from lava.lavacore import LOG, LavaError
from lava.lib.datetime import duration_to_seconds
from .aws import assume_role
from .core import (
    _PYSQL_CONN_HANDLERS,
    db_credentials_getter,
    make_application_name,
    pysql_connector,
)

try:
    import pgdb
except ImportError:
    import lava.lib.dbnone as pgdb

    pgdb.alias = 'PyGreSQL (pgdb)'

try:
    import redshift_connector
except ImportError:
    import lava.lib.dbnone as redshift_connector

    redshift_connector.alias = 'Redshift Connector (AWS)'


__author__ = 'Murray Andrews'


# ------------------------------------------------------------------------------
@db_credentials_getter('redshift')
def get_redshift_cluster_creds_with_iam(
    conn_spec: dict[str, Any], aws_session: boto3.Session = None
) -> tuple[str, str]:
    """
    Get a Redshift username, password using GetClusterCredentials.

    :param conn_spec:       A validated, expanded connection spec.
    :param aws_session:     A boto3 Session. A default is used if not specified.

    :return:                A tuple (username, password).
    """

    if 'database' not in conn_spec:
        raise LavaError('database must be specified')

    if not aws_session:
        aws_session = boto3.Session()

    try:
        duration = int(
            duration_to_seconds(conn_spec.get('password_duration', config('RS_PASSWORD_DURATION')))
        )
    except ValueError:
        raise LavaError('Bad password_duration')

    response = aws_session.client('redshift').get_cluster_credentials(
        DbName=conn_spec['database'],
        DbUser=conn_spec['user'],
        ClusterIdentifier=conn_spec.get('cluster_id', conn_spec['host'].split('.', 1)[0]),
        DurationSeconds=duration,
        AutoCreate=False,
    )
    LOG.debug(
        'Got Redshift password via IAM user={DbUser}, Expires={Expiration}'.format(**response)
    )
    return response['DbUser'], response['DbPassword']


# ------------------------------------------------------------------------------
@db_credentials_getter('redshift-serverless')
def get_redshift_serverless_creds_with_iam(
    conn_spec: dict[str, Any], aws_session: boto3.Session = None
) -> tuple[str, str]:
    """
    Get a Redshift Serverless username, password using GetCredentials.

    This is a somewhat different mechanism from the one provided by Redshift
    provisioned GetClusterCredentials. The latter allows the DB user name to be
    specified but serverless does not permit that. You get stuck with a DB user
    name derived from the IAM name in the form `IAM:user-name` (users) or
    `IAMR:role-name` (roles). To mitigate the restrictiveness of this, we allow
    a `role_arn` to be specified. This role is assumed when generating Redshift
    credentials.

    :param conn_spec:       A validated, expanded connection spec.
    :param aws_session:     A boto3 Session. A default is used if not specified.

    :return:                A tuple (username, password).
    """

    if 'database' not in conn_spec:
        raise LavaError('database must be specified')

    if not aws_session:
        aws_session = boto3.Session()

    db_creds_session = aws_session

    if 'role_arn' in conn_spec:
        assume_role_creds = assume_role(
            role_arn=conn_spec['role_arn'],
            role_session_name=make_application_name(conn_id=conn_spec['conn_id']) or 'lava',
            external_id_ssm_param=conn_spec.get('external_id'),
            # The duration here is the duration of the assume role session - not
            # the duration of the Redshift session. Since we only use the assumed
            # role to immediately get DB credentials, duration here can be short.
            duration='15m',  # 900 seconds is the minimum for assume role - AWS rule
            tags=conn_spec.get('tags'),
            aws_session=aws_session,
        )
        db_creds_session = boto3.Session(
            region_name=conn_spec.get('region', aws_session.region_name), **assume_role_creds
        )

    response = db_creds_session.client('redshift-serverless').get_credentials(
        dbName=conn_spec['database'],
        workgroupName=conn_spec.get('workgroup', conn_spec['host'].split('.', 1)[0]),
        durationSeconds=int(
            duration_to_seconds(conn_spec.get('password_duration', config('RS_PASSWORD_DURATION')))
        ),
    )
    LOG.debug(
        'Got Redshift password via IAM user={dbUser}, Expires={expiration}'.format(**response)
    )
    return response['dbUser'], response['dbPassword']


# ------------------------------------------------------------------------------
@pysql_connector(dialect='redshift', subtype='pg8000')
def py_rs_connect_pg8000(
    conn_spec: dict[str, Any],
    autocommit: bool = False,
    application_name: str = None,
) -> pg8000.Connection:
    """
    Get a pg8000 connection to a Redshift cluster.

    This just uses the postgresql subsystem.

    :param conn_spec:       Pre-expanded connection specification
    :param autocommit:      If True, attempt to enable autocommit. This is
                            database and driver dependent as not all DBs
                            support it (e.g. sqlite3) If False, autocommit is
                            not enabled (the default state for DBAPI 2.0).
    :param application_name: Application name when connecting.

    :return:                A live DB connection

    """

    if not conn_spec.get('database'):
        raise LavaError('database must be specified for Redshift')

    try:
        pg_handler = _PYSQL_CONN_HANDLERS[('postgresql', 'pg8000')]
    except KeyError:
        raise LavaError('No connection handler for postgresql(pg8000)')

    LOG.debug('Connecting to redshift using postgres pg8000')
    return pg_handler(conn_spec, autocommit=autocommit, application_name=application_name)


# ------------------------------------------------------------------------------
# noinspection PyUnusedLocal
@pysql_connector(dialect='redshift', subtype='pygresql')
def py_rs_connect_pygresql(
    conn_spec: dict[str, Any],
    autocommit: bool = False,
    application_name: str = None,
) -> pgdb.Connection:
    """
    Get a pygresql connection to a Redshift cluster.

    !!! danger
        PyGreSQL does not support Redshift and doesn't work with Redshift any more.

    :param conn_spec:       Pre-expanded connection specification
    :param autocommit:      If True, attempt to enable autocommit. This is
                            database and driver dependent as not all DBs
                            support it (e.g. sqlite3) If False, autocommit is
                            not enabled (the default state for DBAPI 2.0).
    :param application_name: Application name when connecting.

    :return:                A live DB connection

    """

    raise LavaError('PyGreSQL no longer supports Redshift')


# ------------------------------------------------------------------------------
@pysql_connector(dialect='redshift', subtype='redshift')
def py_rs_connect_redshift(
    conn_spec: dict[str, Any],
    autocommit: bool = False,
    application_name: str = None,
) -> redshift_connector.Connection:
    """
    Get a Redshift Connector connection to a Redshift cluster.

    This uses the AWS driver.

    :param conn_spec:       Pre-expanded connection specification
    :param autocommit:      If True, attempt to enable autocommit. This is
                            database and driver dependent as not all DBs
                            support it (e.g. sqlite3) If False, autocommit is
                            not enabled (the default state for DBAPI 2.0).
    :param application_name: Application name when connecting.

    :return:                A live DB connection

    """

    if not conn_spec.get('database'):
        raise LavaError('database must be specified for Redshift')

    LOG.debug('Connecting to redshift using Redshift connector')

    db_connect_params = {
        'user': conn_spec['user'],
        'password': conn_spec['password'],
        'host': conn_spec['host'],
        'port': conn_spec['port'],
        'database': conn_spec['database'],
        'ssl': conn_spec.get('ssl', False),
        # This is not well documented by AWS but it is in the interface
        'application_name': application_name or None,
    }

    conn = redshift_connector.connect(**db_connect_params)
    conn.autocommit = autocommit
    return conn
