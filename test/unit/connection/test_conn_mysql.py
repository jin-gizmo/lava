"""Tests for the mysql connector."""

from __future__ import annotations

import re
import subprocess

import pytest  # noqa

from lava.connection.mysql import *
from test.conftest import use_moto


# ------------------------------------------------------------------------------
@pytest.mark.parametrize(
    'ssl_, ssl_mode, expected_ssl_version_re',
    [
        (None, None, None),  # None for expected_ssl_active is "don't care".
        (None, 'require', 'TLS.*'),
        (None, 'verify-ca', 'TLS.*'),
        (None, 'verify-full', 'TLS.*'),
        (True, None, 'TLS.*'),
    ],
)
def test_py_connect_mysql_ok(ssl_, ssl_mode, expected_ssl_version_re, tc, dirs):
    conf = tc.db.mysql_local
    print(conf)
    conn_spec = {
        'conn_id': 'test/mysql-local',
        'description': 'DB connection test',
        'enabled': True,
        'type': 'mysql',
        'host': conf.host,
        'port': conf.port,
        'database': conf.database,
        'user': conf.user,
        'password': os.environ['DB_LAVA_PASSWORD'],
        'ssl_mode': ssl_mode,
    }
    if ssl_mode and ssl_mode.startswith('verify-'):
        conn_spec['ssl_ca_file'] = str(dirs.services / 'mysql/mysql/server.crt')

    # Backward compatibility check
    if ssl_ is not None:
        conn_spec['ssl'] = ssl_

    sql = "SHOW STATUS LIKE 'Ssl_version'"
    with py_connect_mysql(conn_spec, application_name='test-mysql-conn') as conn:
        cur = conn.cursor()
        cur.execute(sql)
        ssl_version = cur.fetchone()[1]
        if expected_ssl_version_re:
            assert re.match(expected_ssl_version_re, ssl_version)
        else:
            # Don't care
            pass


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
def test_py_connect_mysql_bad_cert(ssl_, ssl_mode, exception_msg, tc, dirs):
    """Test when the server doesn't have a cert that can be validated."""

    # Note no host cert provided so our self signed cert won't validate.
    conf = tc.db.mysql_local
    conn_spec = {
        'conn_id': 'test/mysql-local',
        'description': 'DB connection test',
        'enabled': True,
        'type': 'mysql',
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
            py_connect_mysql(conn_spec, application_name='test-mysql-conn')
    else:
        py_connect_mysql(conn_spec, application_name='test-mysql-conn').close()


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
def test_py_connect_mysql_bad_hostname(ssl_, ssl_mode, exception_msg, tc, dirs):
    """Test when the hostname doesn't match."""
    conf = tc.db.mysql_local
    conn_spec = {
        'conn_id': 'test/mysql-local',
        'description': 'DB connection test',
        'enabled': True,
        'type': 'mysql',
        'host': 'localhost',  # This won't match the certificate
        'port': conf.port,
        'database': conf.database,
        'user': conf.user,
        'password': os.environ['DB_LAVA_PASSWORD'],
        'ssl_mode': ssl_mode,
        'ssl_ca_file': str(dirs.services / 'mysql/mysql/server.crt'),
    }
    # Backward compatibility check
    if ssl_ is not None:
        conn_spec['ssl'] = ssl_

    if exception_msg:
        with pytest.raises(Exception, match=exception_msg):
            py_connect_mysql(conn_spec, application_name='test-mysql-conn')
    else:
        py_connect_mysql(conn_spec, application_name='test-mysql-conn').close()


def test_py_connect_mysql_bad_mode(tc, dirs):
    conf = tc.db.mysql_local
    conn_spec = {
        'conn_id': 'test/mysql-local',
        'description': 'DB connection test',
        'enabled': True,
        'type': 'mysql',
        'host': conf.host,
        'port': conf.port,
        'database': conf.database,
        'user': conf.user,
        'password': os.environ['DB_LAVA_PASSWORD'],
        'ssl_mode': 'bad-mode',
        'ssl_ca_file': str(dirs.services / 'mysql/mysql/server.crt'),
    }
    with pytest.raises(ValueError, match=f'Bad ssl_mode: bad-mode'):
        py_connect_mysql(conn_spec, application_name='test-mysql-conn')


def test_py_connect_mysql_no_database(tc, dirs):
    conf = tc.db.mysql_local
    conn_spec = {
        'conn_id': 'test/mysql-local',
        'description': 'DB connection test',
        'enabled': True,
        'type': 'mysql',
        'host': conf.host,
        'port': conf.port,
        'user': conf.user,
        'password': os.environ['DB_LAVA_PASSWORD'],
        'ssl_ca_file': str(dirs.services / 'mysql/mysql/server.crt'),
    }
    with pytest.raises(LavaError, match=f'database must be specified for MySQL'):
        py_connect_mysql(conn_spec, application_name='test-mysql-conn')


# ------------------------------------------------------------------------------
@use_moto
@pytest.mark.parametrize(
    'cli_type, ssl_, ssl_mode, expected_ssl_version_re',
    [
        ('oracle', None, 'require', 'TLS.*'),
        ('oracle', None, 'verify-ca', 'TLS.*'),
        ('oracle', None, 'verify-full', 'TLS.*'),
        ('oracle', True, None, 'TLS.*'),
        ('mariadb', None, 'require', 'TLS.*'),
        ('mariadb', None, 'verify-ca', 'TLS.*'),
        ('mariadb', None, 'verify-full', 'TLS.*'),
        ('mariadb', True, None, 'TLS.*'),
    ],
)
def test_cli_connect_mysql_ok(
    cli_type, ssl_, ssl_mode, expected_ssl_version_re, tc, dirs, tmp_path, set_mysql_docker_cli
):

    # Force use of docker based client
    set_mysql_docker_cli(cli_type, tmp_path)

    aws_session = boto3.Session()
    ssm = aws_session.client('ssm')
    ssm.put_parameter(
        Name='mysql-test-password', Type='String', Value=os.environ['DB_LAVA_PASSWORD']
    )
    conf = tc.db.mysql_local
    conn_spec = {
        'conn_id': 'test/mysql-local',
        'description': 'DB CLI connection test',
        'enabled': True,
        'type': 'mysql',
        'host': conf.host,
        'port': conf.port,
        'database': conf.database,
        'user': conf.user,
        'password': 'mysql-test-password',
        'ssl_mode': ssl_mode,
        # The Oracle client doesn't need this for the non-ssl cases but MariaDB does.
        # The SSL cases always need it.
        'ssl_ca_file': str(dirs.services / 'mysql/mysql/server.crt'),
    }
    # if ssl_mode and ssl_mode.startswith('verify-'):
    #     conn_spec['ssl_ca_file'] = str(dirs.services / 'mysql/mysql/server.crt')
    # Backward compatibility check
    if ssl_ is not None:
        conn_spec['ssl'] = ssl_

    sql = "SHOW STATUS LIKE 'Ssl_version'"
    script_file = cli_connect_mysql(conn_spec, workdir=str(tmp_path), aws_session=aws_session)
    proc = subprocess.run(
        [script_file, '--skip-column-names'],
        capture_output=True,
        timeout=15,
        text=True,
        input=sql,
    )
    assert proc.returncode == 0
    # stdout should be something like 'Ssl_version	TLSv1.3'
    _, ssl_version = re.split(r'\s+', proc.stdout.strip(), 1)
    assert re.match(expected_ssl_version_re, ssl_version)


@use_moto
def test_cli_connect_mysql_bad_ssl_mode(tc, dirs, tmp_path, set_mysql_docker_cli):
    set_mysql_docker_cli('oracle', tmp_path)
    aws_session = boto3.Session()
    ssm = aws_session.client('ssm')
    ssm.put_parameter(
        Name='mysql-test-password', Type='String', Value=os.environ['DB_LAVA_PASSWORD']
    )
    conf = tc.db.mysql_local
    conn_spec = {
        'conn_id': 'test/mysql-local',
        'description': 'DB connection test',
        'enabled': True,
        'type': 'mysql',
        'host': conf.host,
        'port': conf.port,
        'database': conf.database,
        'user': conf.user,
        'password': 'mysql-test-password',
        'ssl_mode': 'bad-mode',
    }

    with pytest.raises(ValueError, match='Bad ssl_mode: bad-mode'):
        cli_connect_mysql(conn_spec, workdir=str(tmp_path), aws_session=aws_session)


@use_moto
def test_cli_connect_mysql_no_database(tc, dirs, tmp_path, set_mysql_docker_cli):
    # Force use of docker based client
    set_mysql_docker_cli('oracle', tmp_path)
    aws_session = boto3.Session()
    ssm = aws_session.client('ssm')
    ssm.put_parameter(
        Name='mysql-test-password', Type='String', Value=os.environ['DB_LAVA_PASSWORD']
    )
    conf = tc.db.mysql_local
    conn_spec = {
        'conn_id': 'test/mysql-local',
        'description': 'DB connection test',
        'enabled': True,
        'type': 'mysql',
        'host': conf.host,
        'port': conf.port,
        'user': conf.user,
        'password': 'mysql-test-password',
    }

    with pytest.raises(LavaError, match='database must be specified for MySQL'):
        cli_connect_mysql(conn_spec, workdir=str(tmp_path), aws_session=aws_session)


@use_moto
def test_cli_connect_mysql_no_passwd(tc, dirs, tmp_path, monkeypatch, set_mysql_docker_cli):
    set_mysql_docker_cli('oracle', tmp_path)
    aws_session = boto3.Session()
    # Absence of password parameter will force an exception.
    conf = tc.db.mysql_local
    conn_spec = {
        'conn_id': 'test/db/mysql/local',
        'description': 'DB connection test',
        'enabled': True,
        'type': 'mysql',
        'host': conf.host,
        'port': conf.port,
        'database': conf.database,
        'user': conf.user,
        'password': 'no-such-parameter',
    }

    with pytest.raises(LavaError, match='Parameter no-such-parameter not found'):
        cli_connect_mysql(conn_spec, workdir=str(tmp_path), aws_session=aws_session)


@use_moto
@pytest.mark.parametrize(
    'cli_type, ssl_, ssl_mode, exception_msg',
    [
        # ('oracle', None, None, None),
        # ('oracle', None, 'require', None),
        # ('oracle', None, 'verify-ca', 'CA certificate is required'),
        # ('oracle', None, 'verify-full', 'CA certificate is required'),
        # ('oracle', True, None, None),
        # MariaDB client is now fussy about always having a valid cert. It used
        # to be more tolerant in the SSL-optional modes
        ('mariadb', None, None, 'TLS/SSL error: self-signed certificate'),
        ('mariadb', None, 'require', 'TLS/SSL error: self-signed certificate'),
        # MariaDB CLI cannot handle verify-ca mode.
        ('mariadb', None, 'verify-full', 'TLS/SSL error: self-signed certificate'),
        ('mariadb', True, None, 'TLS/SSL error: self-signed certificate'),
    ],
)
def test_cli_connect_mysql_bad_cert_fail(
    cli_type, ssl_, ssl_mode, exception_msg, tc, dirs, tmp_path, set_mysql_docker_cli
):
    """Don't configure a cert file."""

    set_mysql_docker_cli(cli_type, tmp_path)
    aws_session = boto3.Session()
    ssm = aws_session.client('ssm')
    ssm.put_parameter(
        Name='mysql-test-password',
        Type='String',
        Value=os.environ['DB_LAVA_PASSWORD'],
    )
    conf = tc.db.mysql_local
    conn_spec = {
        'conn_id': 'test/db/mysql/local',
        'description': 'DB CLI connection test',
        'enabled': True,
        'type': 'mysql',
        'host': conf.host,
        'port': conf.port,
        'database': conf.database,
        'user': conf.user,
        'password': 'mysql-test-password',
        'ssl_mode': ssl_mode,
    }
    # Backward compatibility check
    if ssl_ is not None:
        conn_spec['ssl'] = ssl_

    # Query results are JSON
    sql = "SHOW STATUS LIKE 'Ssl_version'"
    script_file = cli_connect_mysql(conn_spec, workdir=str(tmp_path), aws_session=aws_session)
    proc = subprocess.run(
        [script_file, '--skip-column-names'],
        capture_output=True,
        timeout=15,
        text=True,
        input=sql,
    )
    assert exception_msg or proc.returncode == 0
    if exception_msg:
        exception_msg: str
        assert exception_msg in proc.stderr.strip()


@use_moto
def test_cli_connect_mysql_no_cli_available(tc, dirs, tmp_path, monkeypatch):
    """Don't configure a cert file."""

    # Disable the cache on _mysql_flavour so we can switch from oracle to mariadb
    from lava.connection.mysql import _mysql_flavour

    monkeypatch.setattr('lava.connection.mysql._mysql_flavour', _mysql_flavour.__wrapped__)
    monkeypatch.setattr('lava.connection.mysql.MYSQL_CLI', 'no-mysql-cli-available')

    # ------------------------------
    aws_session = boto3.Session()
    ssm = aws_session.client('ssm')
    ssm.put_parameter(
        Name='mysql-test-password', Type='String', Value=os.environ['DB_LAVA_PASSWORD']
    )
    conf = tc.db.mysql_local
    conn_spec = {
        'conn_id': 'test/mysql-local',
        'description': 'DB CLI connection test',
        'enabled': True,
        'type': 'mysql',
        'host': conf.host,
        'port': conf.port,
        'database': conf.database,
        'user': conf.user,
        'password': 'mysql-test-password',
    }

    # Query results are JSON
    with pytest.raises(LavaError, match='No mysql client available'):
        cli_connect_mysql(conn_spec, workdir=str(tmp_path), aws_session=aws_session)
