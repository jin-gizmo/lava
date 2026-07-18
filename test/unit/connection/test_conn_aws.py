"""Test AWS connector."""

import json
import subprocess
from pathlib import Path

import pytest  # noqa
from lava import LavaError
from lava.connection import get_aws_connection, get_cli_connection


# ------------------------------------------------------------------------------
def test_get_aws_conn(tc):
    conn = get_aws_connection(conn_id=f'{tc.prefix.conn}/aws/ssm', realm=tc.realm)
    assert {'region', 'aws_access_key_id', 'aws_secret_access_key'} <= conn.keys()


# ------------------------------------------------------------------------------
def test_get_aws_conn_fail_wrong_type(tc):
    with pytest.raises(LavaError, match='Must be of type "aws" not .*'):
        get_aws_connection(conn_id=f'{tc.prefix.conn}/docker/base', realm=tc.realm)


# ------------------------------------------------------------------------------
def test_get_aws_cli_conn(tc, tmp_path):
    conn = Path(
        get_cli_connection(
            conn_id=f'{tc.prefix.conn}/aws/ssm', realm=tc.realm, workdir=str(tmp_path)
        )
    )
    assert conn.is_file()
    assert conn.read_text().startswith('#!')


# ------------------------------------------------------------------------------
def test_use_aws_cli_conn(tc, tmp_path):
    conn = get_cli_connection(
        conn_id=f'{tc.prefix.conn}/aws/ssm', realm=tc.realm, workdir=str(tmp_path)
    )

    proc = subprocess.run([conn, 'sts', 'get-caller-identity'], check=True, capture_output=True)
    result = json.loads(proc.stdout)
    assert {'UserId', 'Account', 'Arn'} <= result.keys()
