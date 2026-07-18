"""Test slack utilities"""

from __future__ import annotations

import os
from uuid import uuid4

import pytest
from lava import LavaError
from lava.lib.slack import Slack


# ------------------------------------------------------------------------------
@pytest.mark.parametrize('style', ['plain', 'block', 'attachment', None])
def test_slack_ok(style, realm_info, slack_emulator_client):

    conn_spec = {
        'colour': 'ff7711',  # With or without # is ok
        'conn_id': 'test/slack/local-base',
        'description': 'Slack webhook connection (local emulator)',
        'enabled': True,
        'from': 'Test',
        'preamble': ':volcano:',
        'type': 'slack',
        'webhook_url': os.environ['SLACK_WEBHOOK'],
    }
    if style:
        conn_spec['style'] = style
    slack_conn = Slack(conn_spec, realm_info.realm)
    msg_id = str(uuid4())
    slack_conn.send(f'Msg: {msg_id}', subject=msg_id)
    messages = slack_emulator_client.search_conversation('general', msg_id)
    assert len(messages) == 1


# ------------------------------------------------------------------------------
def test_slack_not_enabled(realm_info, slack_emulator_client):

    conn_spec = {
        'colour': '#ff7711',
        'conn_id': 'test/slack/local-base',
        'description': 'Slack webhook connection (local emulator)',
        'enabled': False,
        'from': 'Test',
        'preamble': ':volcano:',
        'type': 'slack',
        'webhook_url': os.environ['SLACK_WEBHOOK'],
    }
    with pytest.raises(LavaError, match='not enabled'):
        _ = Slack(conn_spec, realm_info.realm)


# ------------------------------------------------------------------------------
def test_slack_wrong_type(realm_info, slack_emulator_client):

    conn_spec = {
        'colour': '#ff7711',
        'conn_id': 'test/slack/local-base',
        'description': 'Slack webhook connection (local emulator)',
        'enabled': True,
        'from': 'Test',
        'preamble': ':volcano:',
        'type': '---',  # Wrong typr
        'webhook_url': os.environ['SLACK_WEBHOOK'],
    }
    with pytest.raises(ValueError, match='not a slack connection'):
        _ = Slack(conn_spec, realm_info.realm)


# ------------------------------------------------------------------------------
def test_slack_bad_style(realm_info, slack_emulator_client):

    conn_spec = {
        'colour': '#ff7711',
        'conn_id': 'test/slack/local-base',
        'description': 'Slack webhook connection (local emulator)',
        'enabled': True,
        'from': 'Test',
        'preamble': ':volcano:',
        'type': 'slack',
        'style': 'bad-style',
        'webhook_url': os.environ['SLACK_WEBHOOK'],
    }
    with pytest.raises(ValueError, match='Bad style bad-style'):
        _ = Slack(conn_spec, realm_info.realm)


# ------------------------------------------------------------------------------
def test_slack_no_msg(realm_info, slack_emulator_client):

    conn_spec = {
        'colour': 'ff7711',  # With or without # is ok
        'conn_id': 'test/slack/local-base',
        'description': 'Slack webhook connection (local emulator)',
        'enabled': True,
        'from': 'Test',
        'preamble': ':volcano:',
        'type': 'slack',
        'webhook_url': os.environ['SLACK_WEBHOOK'],
    }
    slack_conn = Slack(conn_spec, realm_info.realm)
    with pytest.raises(ValueError, match='message must be specified'):
        slack_conn.send(message='')


# ------------------------------------------------------------------------------
def test_slack_bad_style_on_send(realm_info, slack_emulator_client):

    conn_spec = {
        'colour': 'ff7711',  # With or without # is ok
        'conn_id': 'test/slack/local-base',
        'description': 'Slack webhook connection (local emulator)',
        'enabled': True,
        'from': 'Test',
        'preamble': ':volcano:',
        'type': 'slack',
        'webhook_url': os.environ['SLACK_WEBHOOK'],
    }
    slack_conn = Slack(conn_spec, realm_info.realm)
    with pytest.raises(ValueError, match='Bad slack message style: bad-style'):
        slack_conn.send(message='whatever', style='bad-style')
