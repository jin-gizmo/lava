"""Tests for the email connector."""

from __future__ import annotations

import json
from subprocess import run
from urllib.request import urlopen
from uuid import uuid4

from collections.abc import Iterable

import pytest  # noqa
from const import MAILPIT_ADMIN_PORT, MAILPIT_HOST
from lava.connection.email import *


# ------------------------------------------------------------------------------
@pytest.mark.parametrize(
    'conn_name',
    ['smtp-local'],
)
def test_conn_email_py_smtp_ok(conn_name: str, tc, td):
    conn_id = f'{tc.prefix.conn}/email/{conn_name}'
    conn = get_email_connection(conn_id=conn_id, realm=tc.realm)

    msg_id = str(uuid4())
    sender = 'from@example.com'
    to = ['to_1@example.com', 'to_2@example.com']
    attachments = [
        str(td / 'lava.png'),
    ]

    conn.send(
        subject=msg_id,
        message=f'Test message: {msg_id}',
        to=to,
        reply_to='reply@example.com',
        attachments=attachments,
        sender=sender,
    )

    # Hit the Mailpit query endpoint to get a list of all email messages.
    # If you have more than 100,000 messages this will need pagination.
    email_admin_url = f'http://{MAILPIT_HOST}:{MAILPIT_ADMIN_PORT}/api/v1/messages?limit=100000'
    response = urlopen(email_admin_url)
    assert response.getcode() == 200

    all_messages = json.loads(response.read())['messages']
    # ... find our message
    msg = [m for m in all_messages if m.get('Subject') == msg_id]
    assert len(msg) == 1
    assert msg[0]['From']['Address'] == sender
    assert msg[0]['ReplyTo'][0]['Address'] == 'reply@example.com'
    assert {to['Address'] for to in msg[0]['To']} == set(to)
    assert msg[0]['Attachments'] == len(attachments)


# ------------------------------------------------------------------------------
@pytest.mark.parametrize(
    'conn_name, sender, reply_to',
    [
        # This connection has from / reply_to elements
        ('smtp-local', None, []),
        ('smtp-local', 'wotcha@example.com', ['r1@example.com', 'r2@example.com']),
        # This connection has no from / reply_to elements so we must provide a sender
        ('smtp-local-base', 'wotcha@example.com', []),
        ('smtp-local-base', 'wotcha@example.com', ['r1@example.com', 'r2@example.com']),
        ('smtp-local', None, []),
    ],
)
def test_conn_email_cli_smtp_ok(
    conn_name: str,
    sender,  # None defers to connection spec
    reply_to: Iterable[str],  # Empty list defers to connection spec
    tc,
    td,
    tmp_path,
):
    # Mailpit in the container
    conn_id = f'{tc.prefix.conn}/email/{conn_name}'
    conn_spec = get_connection_spec(conn_id, tc.realm)

    conn = cli_connect_email(conn_spec=conn_spec, workdir=str(tmp_path))

    msg_id = str(uuid4())
    to = ['to_1@example.com', 'to_2@example.com']
    attachments = [str(td / 'lava.png')]

    expected_sender = sender or conn_spec['from']
    if reply_to:
        expected_reply_to = set(reply_to)
    else:
        rt = conn_spec.get('reply_to', [])
        expected_reply_to = {rt} if isinstance(rt, str) else set(rt)

    cli_args = [
        conn,
        '--subject',
        msg_id,
        '--realm',
        tc.realm,
        # Recipients
        *[x for addr in to for x in ('--to', addr)],
        # Reply-To
        *[x for addr in reply_to for x in ('--reply-to', addr)],
        # Attachments
        *[x for filename in attachments for x in ('--attach', filename)],
    ]
    if sender:
        cli_args.extend(['--from', sender])
    run(
        cli_args,
        input=f'Test message: {msg_id}',
        text=True,
    )

    # Hit the Mailpit query endpoint to get a list of all email messages.
    # If you have more than 100,000 messages this will need pagination.
    email_admin_url = f'http://{MAILPIT_HOST}:{MAILPIT_ADMIN_PORT}/api/v1/messages?limit=100000'
    response = urlopen(email_admin_url)
    assert response.getcode() == 200

    all_messages = json.loads(response.read())['messages']
    # ... find our message
    msg = [m for m in all_messages if m.get('Subject') == msg_id]
    assert len(msg) == 1
    assert msg[0]['From']['Address'] == expected_sender
    assert {addr['Address'] for addr in msg[0].get('ReplyTo', [])} == expected_reply_to
    assert {to['Address'] for to in msg[0]['To']} == set(to)
    assert msg[0]['Attachments'] == len(attachments)


# ------------------------------------------------------------------------------
def test_conn_ses_cli_ok(tc, td, tmp_path, aws_account_id):
    """
    Test the legacy SES CLI connector.

    This connector has very basic capabilities.
    """

    conn_id = f'{tc.prefix.conn}/ses/base'
    conn_spec = get_connection_spec(conn_id, tc.realm)
    conn = cli_connect_ses(conn_spec=conn_spec, workdir=str(tmp_path))

    msg_id = str(uuid4())
    body = f'Test message: {msg_id}'
    to = ['to_1@example.com', 'to_2@example.com']
    run([conn, '--subject', msg_id, '--to', *to], input=body, text=True)

    # Hit the ministack email admin endpoint to get a list of all email messages
    email_admin_url = f'{os.environ["AWS_ENDPOINT_URL"]}/_ministack/ses/messages?{aws_account_id}'
    response = urlopen(email_admin_url)
    assert response.getcode() == 200

    all_messages = json.loads(response.read())['messages'][aws_account_id]
    # ... find our message
    msg = [m for m in all_messages if m.get('Subject') == msg_id]
    assert len(msg) == 1
    assert msg[0]['Source'] == conn_spec['from']
    assert set(msg[0]['To']) == set(to)
    assert msg[0]['BodyText'].strip() == body


# ------------------------------------------------------------------------------
def test_conn_ses_bad_field(tc, tmp_path):
    conn_id = f'{tc.prefix.conn}/ses/bad-field'
    conn_spec = get_connection_spec(conn_id, tc.realm)
    with pytest.raises(LavaError, match='Unexpected keys:'):
        cli_connect_ses(conn_spec=conn_spec, workdir=str(tmp_path))


# ------------------------------------------------------------------------------
def test_conn_ses_bad_region(tc, tmp_path):
    conn_id = f'{tc.prefix.conn}/ses/bad-region'
    conn_spec = get_connection_spec(conn_id, tc.realm)
    with pytest.raises(LavaError, match='Missing or malformed "region" for SES'):
        cli_connect_ses(conn_spec=conn_spec, workdir=str(tmp_path))


# ------------------------------------------------------------------------------
def test_conn_ses_bad_from(tc, tmp_path):
    conn_id = f'{tc.prefix.conn}/ses/bad-from'
    conn_spec = get_connection_spec(conn_id, tc.realm)
    with pytest.raises(LavaError, match='Missing or malformed "from" for SES'):
        cli_connect_ses(conn_spec=conn_spec, workdir=str(tmp_path))


# ------------------------------------------------------------------------------
def test_conn_email_invalid_fail(tc, tmp_path):
    # A non-email connection will throw an error.
    conn_id = f'{tc.prefix.conn}/slack/base'

    # Python connector first
    with pytest.raises(LavaError, match='Unexpected keys:'):
        get_email_connection(conn_id, tc.realm)

    # Now CLI connector.
    conn_spec = get_connection_spec(conn_id, tc.realm)
    with pytest.raises(LavaError, match='Unexpected keys:'):
        cli_connect_email(conn_spec=conn_spec, workdir=str(tmp_path))


# ------------------------------------------------------------------------------
def test_conn_email_wrong_type(tc):
    conn_id = f'{tc.prefix.conn}/email/wrong-type'
    with pytest.raises(LavaError, match='Must be of type "email" or "ses"'):
        get_email_connection(conn_id, tc.realm)


# ------------------------------------------------------------------------------
def test_conn_email_not_enabled(tc):
    conn_id = f'{tc.prefix.conn}/email/not-enabled'
    with pytest.raises(LavaError, match='Not enabled'):
        get_email_connection(conn_id, tc.realm)
