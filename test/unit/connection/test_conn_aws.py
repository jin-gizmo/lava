"""Test AWS connector."""

import json
import subprocess
from pathlib import Path

import pytest  # noqa

from lava import LavaError
from lava.connection import get_aws_connection, get_aws_session, get_cli_connection
from lava.connection.core import make_application_name


# ------------------------------------------------------------------------------
def test_get_aws_conn(tc):
    conn = get_aws_connection(conn_id=f'{tc.prefix.conn}/aws/ssm', realm=tc.realm)
    assert {'region', 'aws_access_key_id', 'aws_secret_access_key'} <= conn.keys()


# ------------------------------------------------------------------------------
def test_get_aws_session_ssm_ok(tc, aws_account_id):
    aws_session = get_aws_session(conn_id=f'{tc.prefix.conn}/aws/ssm', realm=tc.realm)

    sts = aws_session.client('sts')
    cid = sts.get_caller_identity()

    assert {'UserId', 'Account', 'Arn'} <= cid.keys()
    assert cid['Account'] == aws_account_id
    assert cid['Arn'] == f'arn:aws:iam::{aws_account_id}:root'


# ------------------------------------------------------------------------------
def test_get_aws_session_ssm_missing_param(tc, aws_account_id):
    with pytest.raises(LavaError, match='Parameter no-such-ssm-param not found'):
        get_aws_session(conn_id=f'{tc.prefix.conn}/aws/ssm-missing-param', realm=tc.realm)


# ------------------------------------------------------------------------------
def test_get_aws_session_ssm_bad_access_keys(tc, aws_account_id):
    with pytest.raises(LavaError, match='Must be in format "access_key_id,access_secret_key"'):
        get_aws_session(conn_id=f'{tc.prefix.conn}/aws/ssm-bad-keys', realm=tc.realm)


# ------------------------------------------------------------------------------
def test_get_aws_session_disabled_conn(tc, aws_account_id):
    with pytest.raises(LavaError, match='Not enabled'):
        get_aws_session(conn_id=f'{tc.prefix.conn}/aws/not-enabled', realm=tc.realm)


# ------------------------------------------------------------------------------
def test_get_aws_session_bad_field(tc, aws_account_id):
    with pytest.raises(LavaError, match='Unexpected keys: bad'):
        get_aws_session(conn_id=f'{tc.prefix.conn}/aws/bad-field', realm=tc.realm)


# ------------------------------------------------------------------------------
def test_get_aws_session_no_creds(tc, aws_account_id):
    with pytest.raises(LavaError, match='One of access_keys or role_arn is required'):
        get_aws_session(conn_id=f'{tc.prefix.conn}/aws/no-creds', realm=tc.realm)


# ------------------------------------------------------------------------------
def test_get_aws_session_role_ok(tc, aws_account_id, monkeypatch):
    conn_id = f'{tc.prefix.conn}/aws/local-role'
    job_id = 'my-job-id'
    app_name = make_application_name(conn_id=conn_id, realm=tc.realm, job_id=job_id) or 'ERROR'

    monkeypatch.setenv('LAVA_REALM', tc.realm)
    monkeypatch.setenv('LAVA_JOB_ID', job_id)
    aws_session = get_aws_session(conn_id=conn_id, realm=tc.realm)

    sts = aws_session.client('sts')
    cid = sts.get_caller_identity()

    assert {'UserId', 'Account', 'Arn'} <= cid.keys()
    assert cid['Account'] == aws_account_id
    assert cid['Arn'] == f'arn:aws:sts::123456789012:assumed-role/assume-me/{app_name}'


# ------------------------------------------------------------------------------
def test_get_aws_session_role_missing_param(tc):
    conn_id = f'{tc.prefix.conn}/aws/local-role-missing-param'

    with pytest.raises(LavaError, match='Parameter no-such-ssm-param not found'):
        get_aws_session(conn_id=conn_id, realm=tc.realm)


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
