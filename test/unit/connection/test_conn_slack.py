"""Tests for the slack connector."""

from __future__ import annotations

import subprocess
from uuid import uuid4

import pytest  # noqa
from lava.connection import get_cli_connection
from lava.connection.slack import *


# ------------------------------------------------------------------------------
@pytest.mark.parametrize(
    'conn_name',
    ['local-base'],
)
def test_conn_slack_ok(conn_name, slack_emulator_client, tc):

    conn_id = f'{tc.prefix.conn}/slack/{conn_name}'
    conn = get_slack_connection(conn_id=conn_id, realm=tc.realm)
    msg_id = str(uuid4())
    conn.send(f'Msg: {msg_id}', subject=msg_id)
    messages = slack_emulator_client.search_conversation('general', msg_id)
    assert len(messages) == 1


# ------------------------------------------------------------------------------
@pytest.mark.parametrize(
    'conn_name, error_type, error_msg',
    [
        ('none-such', LavaError, 'No such connection'),
        ('local-base-bad-field', LavaError, 'Unexpected keys: bad'),
        ('local-base-bad-type', LavaError, 'Must be of type "slack"'),
        ('local-base-not-enabled', LavaError, 'Not enabled'),
        ('local-base-bad-webhook', LavaError, 'Parameter .* not found'),
    ],
)
def test_conn_slack_fail(conn_name, error_type, error_msg, tc):

    conn_id = f'{tc.prefix.conn}/slack/{conn_name}'
    with pytest.raises(error_type, match=error_msg):
        _ = get_slack_connection(conn_id=conn_id, realm=tc.realm)


# ------------------------------------------------------------------------------
@pytest.mark.parametrize(
    'conn_name',
    ['local-base'],
)
def test_conn_slack_cli_ok(conn_name, slack_emulator_client, tc, tmp_path, monkeypatch):

    conn_id = f'{tc.prefix.conn}/slack/{conn_name}'
    conn = get_cli_connection(conn_id=conn_id, realm=tc.realm, workdir=str(tmp_path))
    msg_id = str(uuid4())

    monkeypatch.setenv('LAVA_REALM', tc.realm)

    proc = subprocess.run(
        [conn],
        input=msg_id,
        text=True,
        check=True,
        capture_output=True,
    )
    assert proc.returncode == 0
    messages = slack_emulator_client.search_conversation('general', msg_id)
    assert len(messages) == 1


# ------------------------------------------------------------------------------
@pytest.mark.parametrize(
    'conn_name, error_type, error_msg',
    [
        ('none-such', LavaError, 'No such connection'),
        ('local-base-bad-field', LavaError, 'Unexpected keys: bad'),
        ('local-base-not-enabled', LavaError, 'Not enabled'),
    ],
)
def test_conn_slack_cli_fail(conn_name, error_type, error_msg, tc, tmp_path):

    conn_id = f'{tc.prefix.conn}/slack/{conn_name}'
    with pytest.raises(error_type, match=error_msg):
        _ = get_cli_connection(conn_id=conn_id, realm=tc.realm, workdir=str(tmp_path))
