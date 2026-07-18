"""Unit tests for the SQLAlchemy interface to the connector subsystem."""

import pytest
from lava.connection.sqlalchemy import get_sqlalchemy_engine
from lava.exceptions import LavaError
from sqlalchemy import text


# ------------------------------------------------------------------------------
@pytest.mark.parametrize(
    'conn_name',
    [
        'psql/local',
        'oracle/local',
        'mssql/local',
        'mysql/local',
    ],
)
def test_get_sqlalchemy_engine(conn_name: str, tc):

    conn_id = f'{tc.prefix.conn}/db/{conn_name}'
    engine = get_sqlalchemy_engine(conn_id, realm=tc.realm)
    with engine.connect() as conn:
        assert conn.execute(text("SELECT 1200 + 34")).scalar() == 1234


# ------------------------------------------------------------------------------
def test_get_sqlalchemy_engine_bad_engine_arg_fail(tc):
    conn_id = f'{tc.prefix.conn}/db/psql/local'
    with pytest.raises(ValueError, match='Module selection not permitted'):
        _ = get_sqlalchemy_engine(conn_id, realm=tc.realm, module='whatever')


# ------------------------------------------------------------------------------
def test_get_sqlalchemy_engine_bad_conn_id_fail(tc):
    conn_id = 'no-such-conn'
    with pytest.raises(LavaError, match='No such connection'):
        _ = get_sqlalchemy_engine(conn_id, realm=tc.realm)


# ------------------------------------------------------------------------------
# WARNING: This could one day magically succeed rather than fail
def test_get_sqlalchemy_engine_redshift_bad_driver_fail(tc):
    conn_id = f'{tc.prefix.conn}/db/redshift/awsdriver'
    with pytest.raises(LavaError, match=f'Connection {conn_id}: '):
        _ = get_sqlalchemy_engine(conn_id, realm=tc.realm)
