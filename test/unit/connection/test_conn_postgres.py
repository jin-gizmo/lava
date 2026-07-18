"""Tests for the postgres connector."""

from __future__ import annotations

import json
import re
import subprocess

import pytest  # noqa

from lava.connection.postgres import *
from test.conftest import use_moto


# ------------------------------------------------------------------------------
@pytest.mark.parametrize(
    'ssl_, ssl_mode, expected_ssl_active, expected_ssl_version_re',
    [
        (None, None, None, None),  # None for expected_ssl_active is "don't care".
        (None, 'require', True, 'TLS.*'),
        (None, 'verify-ca', True, 'TLS.*'),
        (None, 'verify-full', True, 'TLS.*'),
        (True, None, True, 'TLS.*'),
    ],
)
def test_py_connect_pg8000_ok(
    ssl_, ssl_mode, expected_ssl_active, expected_ssl_version_re, tc, dirs
):
    conf = tc.db.psql_local
    conn_spec = {
        'conn_id': 'test/pg8000-local',
        'description': 'DB connection test',
        'enabled': True,
        'type': 'postgres',
        'host': conf.host,
        'port': conf.port,
        'database': conf.database,
        'user': conf.user,
        'password': os.environ['DB_LAVA_PASSWORD'],
        'ssl_mode': ssl_mode,
    }
    if ssl_mode and ssl_mode.startswith('verify-'):
        conn_spec['ssl_ca_file'] = str(dirs.services / 'postgres/postgres/server.crt')

    # Backward compatibility check
    if ssl_ is not None:
        conn_spec['ssl'] = ssl_

    sql = "SELECT ssl, version FROM pg_stat_ssl WHERE pid = pg_backend_pid();"
    with py_connect_pg8000(conn_spec, application_name='test-pg8000-conn') as conn:
        cur = conn.cursor()
        cur.execute(sql)
        ssl_active, ssl_version = cur.fetchone()
        if expected_ssl_active is not None:
            assert ssl_active is expected_ssl_active
            assert re.match(expected_ssl_version_re, ssl_version)
        else:
            assert isinstance(ssl_active, bool)


# ------------------------------------------------------------------------------
@pytest.mark.parametrize(
    "ssl_, ssl_mode, exception_msg",
    [
        (None, None, None),
        (None, 'require', None),
        (None, 'verify-ca', 'certificate verify failed'),
        (None, 'verify-full', 'certificate verify failed'),
        (True, None, None),
    ],
)
def test_py_connect_pg8000_bad_cert(ssl_, ssl_mode, exception_msg, tc, dirs):
    """Test when the server doesn't have a cert that can be validated."""

    # Note no host cert provided so our self signed cert won't validate.
    conf = tc.db.psql_local
    conn_spec = {
        'conn_id': 'test/pg8000-local',
        'description': 'DB connection test',
        'enabled': True,
        'type': 'postgres',
        'host': conf.host,
        'port': conf.port,
        'database': conf.database,
        'user': conf.user,
        'password': os.environ['DB_LAVA_PASSWORD'],
        'ssl_mode': ssl_mode,
    }
    # Backward compatibility check
    if ssl_ is not None:
        conn_spec['ssl'] = ssl_

    if exception_msg:
        with pytest.raises(Exception, match=exception_msg):
            py_connect_pg8000(conn_spec, application_name='test-pg8000-conn')
    else:
        py_connect_pg8000(conn_spec, application_name='test-pg8000-conn').close()


# ------------------------------------------------------------------------------
@pytest.mark.parametrize(
    "ssl_, ssl_mode, exception_msg",
    [
        (None, None, None),
        (None, 'require', None),
        (None, 'verify-ca', None),
        (None, 'verify-full', 'Hostname mismatch'),
        (True, None, None),
    ],
)
def test_py_connect_pg8000_bad_hostname(ssl_, ssl_mode, exception_msg, tc, dirs):
    """Test when the hostname doesn't match."""
    conf = tc.db.psql_local
    conn_spec = {
        'conn_id': 'test/pg8000-local',
        'description': 'DB connection test',
        'enabled': True,
        'type': 'postgres',
        'host': 'localhost',  # This won't match the certificate
        'port': conf.port,
        'database': conf.database,
        'user': conf.user,
        'password': os.environ['DB_LAVA_PASSWORD'],
        'ssl_mode': ssl_mode,
        'ssl_ca_file': str(dirs.services / 'postgres/postgres/server.crt'),
    }
    # Backward compatibility check
    if ssl_ is not None:
        conn_spec['ssl'] = ssl_

    if exception_msg:
        with pytest.raises(Exception, match=exception_msg):
            py_connect_pg8000(conn_spec, application_name='test-pg8000-conn')
    else:
        py_connect_pg8000(conn_spec, application_name='test-pg8000-conn').close()


def test_py_connect_pg8000_bad_mode(tc, dirs):
    conf = tc.db.psql_local
    conn_spec = {
        'conn_id': 'test/pg8000-local',
        'description': 'DB connection test',
        'enabled': True,
        'type': 'postgres',
        'host': conf.host,
        'port': conf.port,
        'database': conf.database,
        'user': conf.user,
        'password': os.environ['DB_LAVA_PASSWORD'],
        'ssl_mode': 'bad-mode',
        'ssl_ca_file': str(dirs.services / 'postgres/postgres/server.crt'),
    }
    with pytest.raises(ValueError, match=f'Bad ssl_mode: bad-mode'):
        py_connect_pg8000(conn_spec, application_name='test-pg8000-conn')


def test_py_connect_pg8000_no_database(tc, dirs):
    conf = tc.db.psql_local
    conn_spec = {
        'conn_id': 'test/pg8000-local',
        'description': 'DB connection test',
        'enabled': True,
        'type': 'postgres',
        'host': conf.host,
        'port': conf.port,
        'user': conf.user,
        'password': os.environ['DB_LAVA_PASSWORD'],
        'ssl_ca_file': str(dirs.services / 'postgres/postgres/server.crt'),
    }
    with pytest.raises(LavaError, match=f'database must be specified for Postgres'):
        py_connect_pg8000(conn_spec, application_name='test-pg8000-conn')


# ------------------------------------------------------------------------------
@pytest.mark.parametrize(
    'ssl_, ssl_mode, expected_ssl_active, expected_ssl_version_re',
    [
        (None, None, None, None),  # None for expected_ssl_active is "don't care".
        (None, 'require', True, 'TLS.*'),
        (None, 'verify-ca', True, 'TLS.*'),
        (None, 'verify-full', True, 'TLS.*'),
        (True, None, True, 'TLS.*'),
    ],
)
def test_py_connect_pygresql_ok(
    ssl_, ssl_mode, expected_ssl_active, expected_ssl_version_re, tc, dirs
):
    conf = tc.db.psql_local
    conn_spec = {
        'conn_id': 'test/pygresql-local',
        'description': 'DB connection test',
        'enabled': True,
        'type': 'postgres',
        'host': conf.host,
        'port': conf.port,
        'database': conf.database,
        'user': conf.user,
        'password': os.environ['DB_LAVA_PASSWORD'],
        'ssl_mode': ssl_mode,
    }
    if ssl_mode and ssl_mode.startswith('verify-'):
        conn_spec['ssl_ca_file'] = str(dirs.services / 'postgres/postgres/server.crt')

    # Backward compatibility check
    if ssl_ is not None:
        conn_spec['ssl'] = ssl_

    sql = 'SELECT ssl, version FROM pg_stat_ssl WHERE pid = pg_backend_pid();'
    with py_connect_pygresql(conn_spec, application_name='test-pygresql-conn') as conn:
        cur = conn.cursor()
        cur.execute(sql)
        ssl_active, ssl_version = cur.fetchone()
        if expected_ssl_active is not None:
            assert ssl_active is expected_ssl_active
            assert re.match(expected_ssl_version_re, ssl_version)
        else:
            assert isinstance(ssl_active, bool)


def test_py_connect_pygresql_no_database(tc, dirs):
    conf = tc.db.psql_local
    conn_spec = {
        'conn_id': 'test/pygresql-local',
        'description': 'DB connection test',
        'enabled': True,
        'type': 'postgres',
        'host': conf.host,
        'port': conf.port,
        'user': conf.user,
        'password': os.environ['DB_LAVA_PASSWORD'],
        'ssl_ca_file': str(dirs.services / 'postgres/postgres/server.crt'),
    }
    with pytest.raises(LavaError, match=f'database must be specified for Postgres'):
        py_connect_pygresql(conn_spec, application_name='test-pygresql-conn')


# ------------------------------------------------------------------------------
@use_moto
@pytest.mark.parametrize(
    'ssl_, ssl_mode, expected_ssl_active, expected_ssl_version_re',
    [
        (None, None, None, None),  # None for expected_ssl_active is "don't care".
        (None, 'require', True, 'TLS.*'),
        (None, 'verify-ca', True, 'TLS.*'),
        (None, 'verify-full', True, 'TLS.*'),
        (True, None, True, 'TLS.*'),
    ],
)
def test_cli_connect_postgres_ok(
    ssl_,
    ssl_mode,
    expected_ssl_active,
    expected_ssl_version_re,
    tc,
    dirs,
    tmp_path,
    set_psql_docker_cli,
):
    # We run the psql CLI(s) in a docker container.
    set_psql_docker_cli(tmp_path, dirs.services)

    aws_session = boto3.Session()
    ssm = aws_session.client('ssm')
    ssm.put_parameter(
        Name='postgres-test-password', Type='String', Value=os.environ['DB_LAVA_PASSWORD']
    )
    conf = tc.db.psql_local
    conn_spec = {
        'conn_id': 'test/postgres-local',
        'description': 'DB CLI connection test',
        'enabled': True,
        'type': 'postgres',
        'host': conf.host,
        'port': conf.port,
        'database': conf.database,
        'user': conf.user,
        'password': 'postgres-test-password',
        'ssl_mode': ssl_mode,
    }
    if ssl_mode and ssl_mode.startswith('verify-'):
        conn_spec['ssl_ca_file'] = str(dirs.services / 'postgres/postgres/server.crt')
    # Backward compatibility check
    if ssl_ is not None:
        conn_spec['ssl'] = ssl_

    # Query results are JSON
    sql = """
  SELECT json_agg(t)
  FROM (SELECT ssl, version FROM pg_stat_ssl WHERE pid = pg_backend_pid()) t
  """
    script_file = cli_connect_postgres(conn_spec, workdir=str(tmp_path), aws_session=aws_session)
    proc = subprocess.run(
        [script_file, '--tuples-only', '--no-align'],
        capture_output=True,
        timeout=15,
        text=True,
        input=sql,
    )
    assert proc.returncode == 0
    data = json.loads(proc.stdout)[0]
    if expected_ssl_active is not None:
        assert data['ssl'] is expected_ssl_active
        assert re.match(expected_ssl_version_re, data['version'])
    else:
        assert isinstance(data['ssl'], bool)


# ------------------------------------------------------------------------------
@use_moto
@pytest.mark.parametrize(
    'ssl_, ssl_mode, expected_ssl_active, expected_ssl_version_re',
    [
        (None, 'require', True, 'TLS.*'),
    ],
)
def test_cli_connect_postgres_long_passwd_ok(
    ssl_,
    ssl_mode,
    expected_ssl_active,
    expected_ssl_version_re,
    tc,
    dirs,
    tmp_path,
    monkeypatch,
    set_psql_docker_cli,
):
    """Check alternate path for password as an environment variable."""

    monkeypatch.setattr('lava.connection.postgres.PSQL_MAX_PASSWD_LEN', 1)
    # We run the psql CLI(s) in a docker container.
    set_psql_docker_cli(tmp_path)

    aws_session = boto3.Session()
    ssm = aws_session.client('ssm')
    ssm.put_parameter(
        Name='postgres-test-password', Type='String', Value=os.environ['DB_LAVA_PASSWORD']
    )
    conf = tc.db.psql_local
    conn_spec = {
        'conn_id': 'test/postgres-local',
        'description': 'DB CLI connection test',
        'enabled': True,
        'type': 'postgres',
        'host': conf.host,
        'port': conf.port,
        'database': conf.database,
        'user': conf.user,
        'password': 'postgres-test-password',
        'ssl_mode': ssl_mode,
    }
    if ssl_mode and ssl_mode.startswith('verify-'):
        conn_spec['ssl_ca_file'] = str(dirs.services / 'postgres/postgres/server.crt')
    # Backward compatibility check
    if ssl_ is not None:
        conn_spec['ssl'] = ssl_

    # Query results are JSON
    sql = """
  SELECT json_agg(t)
  FROM (SELECT ssl, version FROM pg_stat_ssl WHERE pid = pg_backend_pid()) t
  """
    script_file = cli_connect_postgres(conn_spec, workdir=str(tmp_path), aws_session=aws_session)
    proc = subprocess.run(
        [script_file, '--tuples-only', '--no-align'],
        capture_output=True,
        timeout=15,
        text=True,
        input=sql,
    )
    assert proc.returncode == 0
    data = json.loads(proc.stdout)[0]
    if expected_ssl_active is not None:
        assert data['ssl'] is expected_ssl_active
        assert re.match(expected_ssl_version_re, data['version'])
    else:
        assert isinstance(data['ssl'], bool)


@use_moto
def test_cli_connect_postgres_bad_ssl_mode(tc, dirs, tmp_path):
    aws_session = boto3.Session()
    ssm = aws_session.client('ssm')
    ssm.put_parameter(
        Name='postgres-test-password', Type='String', Value=os.environ['DB_LAVA_PASSWORD']
    )
    conf = tc.db.psql_local
    conn_spec = {
        'conn_id': 'test/postgres-local',
        'description': 'DB connection test',
        'enabled': True,
        'type': 'postgres',
        'host': conf.host,
        'port': conf.port,
        'database': conf.database,
        'user': conf.user,
        'password': 'postgres-test-password',
        'ssl_mode': 'bad-mode',
    }

    with pytest.raises(ValueError, match='Bad ssl_mode: bad-mode'):
        cli_connect_postgres(conn_spec, workdir=str(tmp_path), aws_session=aws_session)


@use_moto
def test_cli_connect_postgres_no_database(tc, dirs, tmp_path):
    aws_session = boto3.Session()
    ssm = aws_session.client('ssm')
    ssm.put_parameter(
        Name='postgres-test-password', Type='String', Value=os.environ['DB_LAVA_PASSWORD']
    )
    conf = tc.db.psql_local
    conn_spec = {
        'conn_id': 'test/postgres-local',
        'description': 'DB connection test',
        'enabled': True,
        'type': 'postgres',
        'host': conf.host,
        'port': conf.port,
        'user': conf.user,
        'password': 'postgres-test-password',
    }

    with pytest.raises(LavaError, match='database must be specified for Postgres'):
        cli_connect_postgres(conn_spec, workdir=str(tmp_path), aws_session=aws_session)


@use_moto
def test_cli_connect_postgres_no_passwd(tc, dirs, tmp_path):
    aws_session = boto3.Session()
    # Absence of password parameter will force an exception.
    conf = tc.db.psql_local
    conn_spec = {
        'conn_id': 'test/postgres-local',
        'description': 'DB connection test',
        'enabled': True,
        'type': 'postgres',
        'host': conf.host,
        'port': conf.port,
        'database': conf.database,
        'user': conf.user,
        'password': 'no-such-parameter',
    }

    with pytest.raises(LavaError, match='Parameter no-such-parameter not found'):
        cli_connect_postgres(conn_spec, workdir=str(tmp_path), aws_session=aws_session)


@use_moto
@pytest.mark.parametrize(
    "ssl_, ssl_mode, exception_msg",
    [
        (None, None, None),
        (None, 'require', None),
        (None, 'verify-ca', 'failed: root certificate file'),
        (None, 'verify-full', 'failed: root certificate file'),
        (True, None, None),
    ],
)
def test_cli_connect_postgres_bad_cert_fail(
    ssl_, ssl_mode, exception_msg, tc, dirs, tmp_path, set_psql_docker_cli
):
    """Don't configure a cert file."""

    # We run the psql CLI(s) in a docker container.
    set_psql_docker_cli(tmp_path)
    aws_session = boto3.Session()
    ssm = aws_session.client('ssm')
    ssm.put_parameter(
        Name='postgres-test-password', Type='String', Value=os.environ['DB_LAVA_PASSWORD']
    )
    conf = tc.db.psql_local
    conn_spec = {
        'conn_id': 'test/postgres-local',
        'description': 'DB CLI connection test',
        'enabled': True,
        'type': 'postgres',
        'host': conf.host,
        'port': conf.port,
        'database': conf.database,
        'user': conf.user,
        'password': 'postgres-test-password',
        'ssl_mode': ssl_mode,
    }
    # Backward compatibility check
    if ssl_ is not None:
        conn_spec['ssl'] = ssl_

    # Query results are JSON
    sql = """
          SELECT json_agg(t)
          FROM (SELECT ssl, version FROM pg_stat_ssl WHERE pid = pg_backend_pid()) t \
          """
    script_file = cli_connect_postgres(conn_spec, workdir=str(tmp_path), aws_session=aws_session)
    proc = subprocess.run(
        [script_file, '--tuples-only', '--no-align'],
        capture_output=True,
        timeout=15,
        text=True,
        input=sql,
    )
    assert exception_msg or proc.returncode == 0
    if exception_msg:
        assert exception_msg in proc.stderr.strip()
