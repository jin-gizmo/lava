"""Test DAG utils."""

from __future__ import annotations

import os
from contextlib import suppress

import pytest
import sqlparse

from lava.lib.dag import *


# ------------------------------------------------------------------------------
@pytest.fixture(scope='module')
def dag_sql(td) -> list[str]:
    """Get the SQL needed to setup our DAG data."""

    return sqlparse.split((td / 'sql/dag.sql').read_text(), strip_semicolon=True)


@pytest.fixture(scope='module')
def sqlite3_dag_db(dag_sql, tmpdir_factory) -> str:
    """Create a temporary SQLite3 DB with a dag and return the filename."""

    dbfile = str(tmpdir_factory.mktemp('db').join('dag.sqlite3'))
    conn = sqlite3.connect(dbfile)
    cursor = conn.cursor()
    for stmt in dag_sql:
        cursor.execute(stmt)
    conn.commit()
    conn.close()
    yield dbfile

    with suppress(Exception):
        os.remove(dbfile)


# ------------------------------------------------------------------------------
def test_load_dag_from_csv(td):
    dag = load_dag_from_csv(str(td / 'dag.csv'))

    assert dag['J4'] == {'J1', 'J3'}


# ------------------------------------------------------------------------------
def test_load_dag_from_xlsx(td):
    dag = load_dag_from_xlsx(str(td / 'dag.xlsx'))

    assert dag['J4'] == {'J1', 'J3'}


# ------------------------------------------------------------------------------
def test_load_dag_from_sqlite3_ok(td, sqlite3_dag_db):
    dag = load_dag_from_sqlite3(sqlite3_dag_db, group='1')
    assert dag['J4'] == {'J1', 'J3'}
    assert 'J3' not in dag

    dag = load_dag_from_sqlite3(sqlite3_dag_db, group='2')
    assert dag['J3'] == {'J1'}


# ------------------------------------------------------------------------------
def test_load_dag_from_sqlite3_bad(td, sqlite3_dag_db):

    with pytest.raises(ValueError, match='Bad table name'):
        load_dag_from_sqlite3(sqlite3_dag_db, table='bad-table-name')
    with pytest.raises(sqlite3.OperationalError, match='no such table'):
        load_dag_from_sqlite3(sqlite3_dag_db, table='no_such_table')
    with pytest.raises(ValueError, match='Only alphanumerics allowed'):
        load_dag_from_sqlite3(sqlite3_dag_db, group='bad-group')


# ------------------------------------------------------------------------------
@pytest.mark.parametrize(
    'conn_id_base',
    [
        'db/psql/local',
        # 'psql-local-pygresql',
        'db/mysql/local',
    ],
)
def test_load_dag_from_lava_conn(conn_id_base, tc):
    dag = load_dag_from_lava_conn(
        conn_id=f'{tc.prefix.conn}/{conn_id_base}',
        realm=tc.realm,
        table='lava.dag',
    )
    assert dag['J4'] == {'J1', 'J3'}
