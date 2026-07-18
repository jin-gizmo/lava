"""Tests for the Oracle connector."""

from __future__ import annotations

import logging
import subprocess

import pytest  # noqa

from bin.lava.lavacore import LOGNAME
from lava.connection.oracle import *
from test.conftest import use_moto


# ------------------------------------------------------------------------------
@pytest.mark.parametrize(
    'ssl_mode, mode, expected_keys, expected_dn_match',
    [
        ('require', 'thin', {'ssl_context', 'ssl_server_dn_match'}, False),
        ('verify-ca', 'thin', {'ssl_context', 'ssl_server_dn_match'}, False),
        ('verify-full', 'thin', {'ssl_context', 'ssl_server_dn_match'}, True),
        ('verify-full', 'thick', {'ssl_server_dn_match'}, True),
    ],
)
def test_marshal_ssl_params_ok(ssl_mode, mode, expected_keys: set[str], expected_dn_match, dirs):
    ssl_params = marshal_ssl_params(ssl_mode, mode=mode)  # noqa
    assert set(ssl_params) == set(expected_keys)
    assert ssl_params.get('ssl_server_dn_match') is expected_dn_match


def test_marshal_ssl_params_bad_mode():
    with pytest.raises(ValueError, match='Bad Oracle connection mode'):
        ssl_params = marshal_ssl_params('whatever', mode='bad-mode')  # noqa


def test_marshal_ssl_params_thick_bad_ssl_mode():
    with pytest.raises(LavaError, match='ssl_mode=require is not supported .* in thick mode'):
        ssl_params = marshal_ssl_params('require', mode='thick')  # noqa


def test_marshal_ssl_params_thick_ca_file_not_allowed():
    with pytest.raises(LavaError, match='ssl_ca_file is not supported .* in thick mode'):
        ssl_params = marshal_ssl_params('verify-full', ssl_ca_file='bad', mode='thick')  # noqa


# ------------------------------------------------------------------------------
@pytest.mark.parametrize(
    'ssl_mode, mode, expected_extra_keys',
    [
        (None, 'thin', {'protocol'}),
        ('verify-ca', 'thin', {'protocol', 'ssl_context', 'ssl_server_dn_match'}),
        ('verify-full', 'thin', {'protocol', 'ssl_context', 'ssl_server_dn_match'}),
    ],
)
def test_marshal_connect_params_ok(ssl_mode, mode, expected_extra_keys):
    conn_spec = {
        'host': 'example.com',
        'port': 1521,
        'user': 'nobody',
        'password': '...',
    }
    # noinspection PyTypeChecker
    marshalled_params = marshal_connect_params(conn_spec | {'ssl_mode': ssl_mode}, mode=mode)

    assert {k for k, v in marshalled_params.items() if v is not None} == set(
        conn_spec
    ) | expected_extra_keys


# ------------------------------------------------------------------------------
@pytest.mark.parametrize(
    'ssl_, ssl_mode, port, expected_protocol',
    [
        (None, None, 1521, 'tcp'),
        (None, 'require', 2484, 'tcps'),
        (None, 'verify-ca', 2484, 'tcps'),
        (None, 'verify-full', 2484, 'tcps'),
        (True, None, 2484, 'tcps'),
    ],
)
def test_py_connect_oracledb_ok(ssl_, ssl_mode, port, expected_protocol, tc, dirs):
    conf = tc.db.oracle_local
    conn_spec = {
        'conn_id': 'test/oracle-local',
        'description': 'DB connection test',
        'enabled': True,
        'type': 'oracle',
        'host': conf.host,
        'port': port,
        'service_name': conf.service_name,
        'user': conf.user,
        'password': os.environ['DB_LAVA_PASSWORD'],
        'ssl_mode': ssl_mode,
        'ssl_ca_file': str(dirs.services / 'oracle/oracle/server.crt'),
    }
    # Backward compatibility check
    if ssl_ is not None:
        conn_spec['ssl'] = ssl_

    sql = "SELECT sys_context('USERENV', 'NETWORK_PROTOCOL') AS network_protocol"
    with py_connect_oracledb(conn_spec, application_name='test-oracle-conn') as conn:
        cur = conn.cursor()
        cur.execute(sql)
        actual_protocol = cur.fetchone()[0]
        assert actual_protocol == expected_protocol


def test_py_connect_oracledb_bad_mode(tc, dirs):
    conf = tc.db.oracle_local
    conn_spec = {
        'conn_id': 'test/oracle-local',
        'description': 'DB connection test',
        'enabled': True,
        'type': 'oracle',
        'host': conf.host,
        'port': 1521,
        'service_name': conf.service_name,
        'user': conf.user,
        'password': os.environ['DB_LAVA_PASSWORD'],
        'ssl_mode': 'bad-mode',
        'ssl_ca_file': str(dirs.services / 'oracle/oracle/server.crt'),
    }
    with pytest.raises(ValueError, match=f'Bad ssl_mode: bad-mode'):
        py_connect_oracledb(conn_spec, application_name='test-oracle-conn')


# ------------------------------------------------------------------------------
@pytest.mark.parametrize(
    'ssl_mode, port, expected_protocol',
    [
        (None, 1521, 'tcp'),
        ('require', 2484, 'tcps'),
        ('verify-ca', 2484, 'tcps'),
        ('verify-full', 2484, 'tcps'),
    ],
)
def test_py_connect_cx_oracle_ok(ssl_mode, port, expected_protocol, tc, dirs, caplog):
    conf = tc.db.oracle_local
    conn_spec = {
        'conn_id': 'test/oracle-local',
        'description': 'DB connection test',
        'enabled': True,
        'type': 'oracle',
        'host': conf.host,
        'port': port,
        'service_name': conf.service_name,
        'user': conf.user,
        'password': os.environ['DB_LAVA_PASSWORD'],
        'ssl_mode': ssl_mode,
        'ssl_ca_file': str(dirs.services / 'oracle/oracle/server.crt'),
    }
    sql = "SELECT sys_context('USERENV', 'NETWORK_PROTOCOL') AS network_protocol"
    with caplog.at_level(logging.WARNING, logger=LOGNAME):
        with py_connect_cx_oracle(conn_spec, application_name='test-oracle-conn') as conn:
            cur = conn.cursor()
            cur.execute(sql)
            actual_protocol = cur.fetchone()[0]
            assert actual_protocol == expected_protocol
        assert 'Deprecation warning' in caplog.text


# ------------------------------------------------------------------------------
@use_moto
@pytest.mark.parametrize(
    'ssl_mode, port, expected_protocol',
    [
        # We can't test any of the TCPS modes using our local self signed cert in thick mode.
        (None, 1521, 'tcp'),
    ],
)
def test_cli_connect_oracle_ok(
    ssl_mode, port, expected_protocol, tc, dirs, tmp_path, set_sqlplus_docker_cli
):
    # Run the sqlplus CLI in a docker container.
    set_sqlplus_docker_cli(tmp_path)
    aws_session = boto3.Session()
    ssm = aws_session.client('ssm')
    ssm.put_parameter(
        Name='oracle-test-password', Type='String', Value=os.environ['DB_LAVA_PASSWORD']
    )
    conf = tc.db.oracle_local
    conn_spec = {
        'conn_id': 'test/oracle-local',
        'description': 'DB connection test',
        'enabled': True,
        'type': 'oracle',
        'host': conf.host,
        'port': port,
        'service_name': conf.service_name,
        'user': conf.user,
        'password': 'oracle-test-password',
        'ssl_mode': ssl_mode,
    }
    sql = """
set heading off
set pagesize 0
SELECT sys_context('USERENV', 'NETWORK_PROTOCOL') AS network_protocol;
"""

    script_file = cli_connect_oracle(conn_spec, workdir=str(tmp_path), aws_session=aws_session)
    proc = subprocess.run(
        [script_file],
        capture_output=True,
        check=True,
        timeout=15,
        text=True,
        input=sql,
    )
    assert proc.returncode == 0
    assert proc.stdout.strip() == expected_protocol


@use_moto
def test_cli_connect_oracle_bad_ssl_mode(tc, dirs, tmp_path):
    aws_session = boto3.Session()
    ssm = aws_session.client('ssm')
    ssm.put_parameter(
        Name='oracle-test-password', Type='String', Value=os.environ['DB_LAVA_PASSWORD']
    )
    conf = tc.db.oracle_local
    conn_spec = {
        'conn_id': 'test/oracle-local',
        'description': 'DB connection test',
        'enabled': True,
        'type': 'oracle',
        'host': conf.host,
        'port': 1521,
        'service_name': conf.service_name,
        'user': conf.user,
        'password': 'oracle-test-password',
        'ssl_mode': 'bad-mode',
    }

    with pytest.raises(LavaError, match='Bad ssl_mode: bad-mode'):
        cli_connect_oracle(conn_spec, workdir=str(tmp_path), aws_session=aws_session)


@use_moto
def test_cli_connect_oracle_no_passwd(tc, dirs, tmp_path):
    aws_session = boto3.Session()
    # Absence of password parameter will force an exception.
    conf = tc.db.oracle_local
    conn_spec = {
        'conn_id': 'test/oracle-local',
        'description': 'DB connection test',
        'enabled': True,
        'type': 'oracle',
        'host': conf.host,
        'port': 1521,
        'service_name': conf.service_name,
        'user': conf.user,
        'password': 'no-such-parameter',
        'ssl_mode': 'whatever',
    }

    with pytest.raises(LavaError, match='Parameter no-such-parameter not found'):
        cli_connect_oracle(conn_spec, workdir=str(tmp_path), aws_session=aws_session)
