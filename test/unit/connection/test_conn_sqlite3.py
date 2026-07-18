"""Test SQLite3 connector."""

import sqlite3
import subprocess
from pathlib import Path

import boto3
import pytest  # noqa

import lava.config
from lava import LavaError
from lava.connection.sqlite3 import (
    Sqlite3Connection,
    cli_connect_sqlite3,
    fake_creds,
    py_connect_sqlite3,
)
from test.conftest import use_moto

BUCKET = 'mock.bucket'
KEY = 'test.sqlite3'
REGION = 'us-east-1'


# ------------------------------------------------------------------------------
@pytest.fixture
@use_moto
def s3_client():
    """Create a mock S3 client."""
    return boto3.client('s3', region_name=REGION)


# ------------------------------------------------------------------------------
@pytest.fixture
def sqlite_db_local(tmp_path) -> Path:
    """Create a simple SQLite DB."""
    db_file = tmp_path / KEY
    conn = sqlite3.connect(db_file)
    cursor = conn.cursor()
    cursor.execute('CREATE TABLE x (a, b)')
    for values in (('A', 'B'), ('AA', 'BB')):
        cursor.execute('INSERT INTO x VALUES (?, ?)', values)
    conn.commit()
    conn.close()
    return db_file


# ------------------------------------------------------------------------------
@use_moto
def test_db_in_s3(s3_client, sqlite_db_local, tmp_path, monkeypatch):

    s3_client.create_bucket(Bucket=BUCKET)
    s3_client.put_object(Bucket=BUCKET, Key=KEY, Body=sqlite_db_local.read_bytes())
    monkeypatch.setenv('TMPDIR', str(tmp_path))
    monkeypatch.setitem(lava.config.__config__, 'TMPDIR', str(tmp_path))

    with Sqlite3Connection(f's3://{BUCKET}/{KEY}') as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT COUNT(*) FROM x')
        assert cursor.fetchone()[0] == 2

    with Sqlite3Connection(f's3://{BUCKET}/{KEY}') as conn:
        # Add a row so DB needs to upload
        cursor = conn.cursor()
        cursor.execute('INSERT INTO x VALUES (?, ?)', ('AAA', 'BBB'))
        cursor.execute('SELECT COUNT(*) FROM x')
        conn.commit()
        assert cursor.fetchone()[0] == 3

    # Try download a non-existent db
    with pytest.raises(LavaError, match='Download failed.* Not Found'):
        Sqlite3Connection(f's3://{BUCKET}/nonesuch')


# ------------------------------------------------------------------------------
@use_moto
def test_db_in_s3_fail(s3_client, sqlite_db_local, tmp_path, monkeypatch):
    """Test failed upload on a changed DB."""

    s3_client.create_bucket(Bucket=BUCKET)
    s3_client.put_object(Bucket=BUCKET, Key=KEY, Body=sqlite_db_local.read_bytes())
    monkeypatch.setenv('TMPDIR', str(tmp_path))
    monkeypatch.setitem(lava.config.__config__, 'TMPDIR', str(tmp_path))

    with pytest.raises(LavaError, match='NoSuchBucket'):
        with Sqlite3Connection(f's3://{BUCKET}/{KEY}') as conn:
            cursor = conn.cursor()
            cursor.execute('INSERT INTO x VALUES (?, ?)', ('AAA', 'BBB'))
            conn.commit()
            # Break the upload process
            conn.bucket = 'no-such-bucket'


# ------------------------------------------------------------------------------
def test_db_local(sqlite_db_local, tmp_path):
    with Sqlite3Connection(str(sqlite_db_local)) as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT COUNT(*) FROM x')
        assert cursor.fetchone()[0] == 2


# ------------------------------------------------------------------------------
@use_moto
def test_py_connect_sqlite3(s3_client, sqlite_db_local, tmp_path, monkeypatch):

    s3_client.create_bucket(Bucket=BUCKET)
    s3_client.put_object(Bucket=BUCKET, Key=KEY, Body=sqlite_db_local.read_bytes())
    monkeypatch.setenv('TMPDIR', str(tmp_path))
    monkeypatch.setitem(lava.config.__config__, 'TMPDIR', str(tmp_path))
    conn_spec = {'host': f's3://{BUCKET}/{KEY}'}

    with py_connect_sqlite3(conn_spec, autocommit=True) as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT COUNT(*) FROM x')
        assert cursor.fetchone()[0] == 2
        # Note no commit here to verify autocommit.
        cursor.execute('INSERT INTO x VALUES (?, ?)', ('AAA', 'BBB'))

    with py_connect_sqlite3(conn_spec) as conn:
        # Add a row so DB needs to upload
        cursor = conn.cursor()
        cursor.execute('SELECT COUNT(*) FROM x')
        assert cursor.fetchone()[0] == 3


# ------------------------------------------------------------------------------
def test_cli_connect_sqlite3(sqlite_db_local, tmp_path):
    # Mock up a conn spec
    conn_spec = {
        'conn_id': 'not-used',
        'type': 'sqlite3',
        'enabled': True,
        'host': str(sqlite_db_local),
        'user': fake_creds({})[0],
        'port': 1234,
    }

    conn = cli_connect_sqlite3(conn_spec, str(tmp_path))
    proc = subprocess.run(
        [conn, '-ascii', '-noheader'],
        input='SELECT COUNT(*) FROM x',
        text=True,
        check=True,
        capture_output=True,
    )
    assert proc.stdout.strip() == '2'


# ------------------------------------------------------------------------------
def test_cli_connect_sqlite3_bad_spec(sqlite_db_local, tmp_path):
    # Mock up a conn spec
    conn_spec = {
        'conn_id': 'not-used',
        'type': 'sqlite3',
        'enabled': True,
        'user': fake_creds({})[0],
        'port': 1234,
    }

    with pytest.raises(LavaError, match='Missing keys: host'):
        cli_connect_sqlite3(conn_spec, str(tmp_path))


# ------------------------------------------------------------------------------
def test_cli_connect_sqlite3_bad_filename(sqlite_db_local, tmp_path):
    # Mock up a conn spec
    conn_spec = {
        'conn_id': 'not-used',
        'type': 'sqlite3',
        'enabled': True,
        'host': "No'quotes please",
        'user': fake_creds({})[0],
        'port': 1234,
    }

    with pytest.raises(LavaError, match='Invalid database file'):
        cli_connect_sqlite3(conn_spec, str(tmp_path))
