"""SqlAlchemy interface for the database connectors."""

__author__ = 'Murray Andrews'

from functools import partial

import boto3
import sqlalchemy

from lava.lavacore import LavaError
from .core import LOG, _get_pysql_connection, get_sql_conn_spec, make_application_name


# ------------------------------------------------------------------------------
def get_sqlalchemy_engine(
    conn_id: str,
    realm: str,
    aws_session: boto3.Session = None,
    application_name: str = None,
    **kwargs,
) -> sqlalchemy.engine.Engine:
    """
    Get an SQLalchemy Engine() instance for the specified SQL database.

    The specifics depend on the underlying database type as specified on the
    connection info.

    :param conn_id:         Connection ID
    :param realm:           Realm
    :param aws_session:     A boto3 Session().
    :param application_name: Application name when connecting.
    :param kwargs:          All other args are passed to sqlalchemy.create_engine.
                            Be careful.

    :return:                An SQLalchemy
                            [Engine](https://docs.sqlalchemy.org/en/20/core/connections.html#sqlalchemy.engine.Engine)
                            instance for the specified SQL database.
    """

    if 'module' in kwargs:
        raise ValueError('get_sqlalchemy_engine: Module selection not permitted')

    try:
        conn_spec = get_sql_conn_spec(conn_id, realm, aws_session=aws_session)
    except Exception as e:
        raise LavaError(f'Connection {conn_id}: {e}')

    # Construct a connection creator
    conn_creator = partial(
        _get_pysql_connection,
        conn_spec=conn_spec,
        # We don't know job_id. In some situations, may be able to get from environment.
        application_name=application_name or make_application_name(conn_id=conn_id, realm=realm),
    )
    dialect = conn_spec['dialect']
    subtype = conn_spec['subtype']

    LOG.debug(f'SQLAlchemy: {dialect}+{subtype}://')
    try:
        return sqlalchemy.create_engine(f'{dialect}+{subtype}://', creator=conn_creator, **kwargs)
    except Exception as e:
        raise LavaError(f'Connection {conn_id}: {e}')
