"""Test the DB utilities."""

from __future__ import annotations

from contextlib import closing
from time import time

import pytest  # noqa

from lava.connection import get_connection_spec
from lava.lib.db import *


# ------------------------------------------------------------------------------
@pytest.fixture(scope='module')
def test_table() -> str:
    """Create a safe unique table name."""
    return f'tmp_{str(time()).replace(".","_")}'


# ------------------------------------------------------------------------------
def test_read_manifest(tc, s3):
    manifest_file = s3.payloads / tc.prefix.payload / 'misc.rsc' / 'custard.csv.manifest'

    manifest = read_manifest(manifest_file.bucket, manifest_file.key)
    print(manifest)

    assert len(manifest) == 1
    assert manifest[0] == (
        (s3.payloads / tc.prefix.payload / 'data.raw' / 'custard100.csv.gz').bucket,
        (s3.payloads / tc.prefix.payload / 'data.raw' / 'custard100.csv.gz').key,
    )


# ------------------------------------------------------------------------------
@pytest.mark.local
@pytest.mark.parametrize(
    'conn_type, conn_name, schema',
    [
        ('postgres', 'db/psql/local', 'lava'),
        ('mssql', 'db/mssql/local', 'lava'),
    ],
)
def test_db_handler(
    conn_type: str,
    conn_name: str,
    schema: str,
    tc,
    tmp_path,
    test_table,
):
    conn_spec = get_connection_spec(f'{tc.prefix.conn}/{conn_name}', tc.realm)

    with closing(
        Database.handler(conn_type, conn_spec=conn_spec, realm=tc.realm, tmpdir=tmp_path)
    ) as db:
        db: Database

        assert db.table_exists(schema, 'custard')
        assert not db.table_exists(schema, 'no_such_table')
        assert not db.table_exists(schema, 'no_such_table')

        db.create_table(schema, test_table, ['x VARCHAR(10)', 'y VARCHAR(10)'])
        assert db.table_exists(schema, test_table)
        assert db.columns(schema, test_table) == ['x', 'y']
        with pytest.raises(ValueError, match='Bad schema name'):
            db.columns("no'quotes'pls", 'whatever')
        with pytest.raises(ValueError, match='Bad table name'):
            db.columns(schema, "no'quotes'pls")

        assert db.table_is_empty(schema, test_table)
        assert not db.table_is_empty(schema, 'custard')

        # Add some data to our temp table
        db.cursor.execute(f"INSERT INTO {db.object_name(schema, test_table)} VALUES ('X', 'Y')")
        db.conn.commit()
        assert not db.table_is_empty(schema, test_table)

        db.truncate_table(schema, test_table)
        assert db.table_is_empty(schema, test_table)

        db.drop_table(schema, test_table)
        assert not db.table_exists(schema, test_table)

        with pytest.raises(ValueError, match='Bad schema name'):
            db.table_exists("no'quotes'pls", 'whatever')
        with pytest.raises(ValueError, match='Bad table name'):
            db.table_exists(schema, "no'quotes'pls")


# ------------------------------------------------------------------------------
@pytest.mark.local
@pytest.mark.parametrize(
    'conn_type, conn_name, schema, copy_args',
    [
        ('postgres', 'db/psql/local', 'lava', ['FORMAT CSV', "DELIMITER ','", 'HEADER']),
        ('postgres', 'db/psql/local', 'lava', ['FORMAT CSV', 'FORCE_NULL *', 'HEADER']),
        ('mssql', 'db/mssql/local', 'lava', ["DELIMITER ','", 'HEADER']),
        ('mssql', 'db/mssql/local', 'lava', ["DELIMITER ','", 'HEADER']),
    ],
)
def test_db_handler_copy_from_s3(
    conn_type: str,
    conn_name: str,
    schema: str,
    copy_args: list[str],
    tc,
    tmp_path,
    realm_info,
    s3,
):
    conn_spec = get_connection_spec(f'{tc.prefix.conn}/{conn_name}', tc.realm)
    s3_data_file = s3.payloads / tc.prefix.payload / 'data.raw' / 'custard100.csv'

    with closing(
        Database.handler(conn_type, conn_spec=conn_spec, realm=tc.realm, tmpdir=tmp_path)
    ) as db:
        db: Database

        table_name = db.object_name(schema, "custard_tmp")
        db.cursor.execute(f'DELETE FROM {table_name}')
        events = db.copy_from_s3(
            schema,
            'custard_tmp',
            s3_data_file.bucket,
            s3_data_file.key,
            copy_args=copy_args,
            min_size=1,
        )
        assert events
        db.cursor.execute(f'SELECT COUNT(*) FROM {table_name}')
        assert db.cursor.fetchone()[0] > 0
        db.conn.commit()


# ------------------------------------------------------------------------------
@pytest.mark.local
@pytest.mark.parametrize(
    'conn_type, conn_name, schema, copy_args',
    [
        ('postgres', 'db/psql/local', 'lava', ['MANIFEST', 'FORMAT CSV', 'GZIP', 'HEADER']),
        ('mssql', 'db/mssql/local', 'lava', ['MANIFEST', 'HEADER', 'GZIP']),
    ],
)
def test_db_handler_copy_from_s3_manifest(
    conn_type: str,
    conn_name: str,
    schema: str,
    copy_args: list[str],
    tc,
    tmp_path,
    realm_info,
    s3,
):
    manifest_file = s3.payloads / tc.prefix.payload / 'misc.rsc' / 'custard.csv.manifest'
    conn_spec = get_connection_spec(f'{tc.prefix.conn}/{conn_name}', tc.realm)

    with closing(
        Database.handler(conn_type, conn_spec=conn_spec, realm=tc.realm, tmpdir=tmp_path)
    ) as db:
        db: Database

        db.cursor.execute(f'DELETE FROM {db.object_name(schema, "custard_tmp")}')
        events = db.copy_from_s3(
            schema,
            'custard_tmp',
            manifest_file.bucket,
            manifest_file.key,
            copy_args=copy_args,
        )
        assert events
        db.cursor.execute(f'SELECT COUNT(*) FROM {db.object_name(schema, "custard_tmp")}')
        assert db.cursor.fetchone()[0] == 100
        db.conn.commit()


# ------------------------------------------------------------------------------
@pytest.mark.local
@pytest.mark.parametrize('conn_name', ['db/psql/local'])
def test_get_query_to_dict(conn_name: str, tc):
    conn = get_pysql_connection(f'{tc.prefix.conn}/{conn_name}', realm=tc.realm)

    results = list(
        query_to_dict(conn.cursor(), 'SELECT ID, CustardClubNo, GivenName FROM CUSTARD LIMIT 5')
    )
    assert len(results) == 5
    assert {k.lower() for k in results[0].keys()} == {'id', 'custardclubno', 'givenname'}
