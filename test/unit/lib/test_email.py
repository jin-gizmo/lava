"""Test the email utils functions"""

import json
from urllib.request import urlopen
from uuid import uuid4

import pytest
from const import MAILPIT_ADMIN_PORT, MAILPIT_HOST, MAILPIT_SMTP_PORT
from lava.lib.email import *


# ------------------------------------------------------------------------------
@pytest.mark.parametrize(
    'filename, expected',
    [
        ('no-suffix', ('application', 'octet-stream')),
        ('a/b.html', ('text', 'html')),
        ('a/b.Png', ('image', 'png')),
    ],
)
def test_content_type(filename, expected):
    assert content_type(filename) == expected


# ------------------------------------------------------------------------------
@pytest.mark.parametrize(
    'type_, subtype',
    [
        ('email', 'ses'),
        # ('email', None),
        # ('ses', None),
    ],
)
def test_ses_emailer(type_, subtype, aws_account_id, td):
    """Test with SES email handler."""
    conn_spec = {
        'conn_id': 'test',
        'enabled': True,
        'type': type_,
        "configuration_set": 'lava-test',
    }
    if subtype:
        conn_spec['subtype'] = subtype

    msg_id = str(uuid4())
    sender = 'from@example.com'
    to = ['to_1@example.com', 'to_2@example.com']
    # WARNING: The ministack SES emulator doesn't handle text attachments
    #          properly. It confuses them with the body.
    attachments = [
        EmailAttachment('att1.txt', 'Attachment 1'),
        str(td / 'f1.txt'),
    ]

    with Emailer.handler(conn_spec, realm='test', sender=sender) as emailer:
        emailer.send(
            subject=msg_id, message=f'Test message: {msg_id}', to=to, attachments=attachments
        )

    # Hit the ministack email admin endpoint to get a list of all email messages
    email_admin_url = f'{os.environ["AWS_ENDPOINT_URL"]}/_ministack/ses/messages?{aws_account_id}'
    response = urlopen(email_admin_url)
    assert response.getcode() == 200
    all_messages = json.loads(response.read())['messages'][aws_account_id]
    # ... find our message
    msg = [m for m in all_messages if m.get('Subject') == msg_id]
    assert len(msg) == 1
    assert msg[0]['Source'] == sender
    assert set(msg[0]['To']) == set(to)


# ------------------------------------------------------------------------------
def test_ses_legacy_emailer(aws_account_id, td):
    """Test with SES email handler."""
    conn_spec = {
        'conn_id': 'test',
        'enabled': True,
        'type': 'ses',
    }

    msg_id = str(uuid4())
    sender = 'from@example.com'
    to = ['to_1@example.com', 'to_2@example.com']

    with AwsSesLegacy(conn_spec, realm='test', sender=sender) as emailer:
        emailer.send(subject=msg_id, message=f'Test message: {msg_id}', to=to)

    # Hit the ministack email admin endpoint to get a list of all email messages
    email_admin_url = f'{os.environ["AWS_ENDPOINT_URL"]}/_ministack/ses/messages?{aws_account_id}'
    response = urlopen(email_admin_url)
    assert response.getcode() == 200

    all_messages = json.loads(response.read())['messages'][aws_account_id]
    # ... find our message
    msg = [m for m in all_messages if m.get('Subject') == msg_id]
    assert len(msg) == 1
    assert msg[0]['Source'] == sender
    assert set(msg[0]['To']) == set(to)


# ------------------------------------------------------------------------------
def test_emailer_bad_subtype(aws_account_id):
    """Test with SES email handler."""
    conn_spec = {
        'conn_id': 'test',
        'enabled': True,
        'type': 'email',
        'subtype': 'bad-subtype',
        "configuration_set": 'lava-test',
    }

    sender = 'from@example.com'
    with pytest.raises(LavaError, match='No email handler for type/subtype email/bad-subtype'):
        Emailer.handler(conn_spec, realm='test', sender=sender)


# ------------------------------------------------------------------------------
def test_emailer_bad_type(aws_account_id):
    """Test with SES email handler."""
    conn_spec = {
        'conn_id': 'test',
        'enabled': True,
        'type': 'bad-type',
        "configuration_set": 'lava-test',
    }

    sender = 'from@example.com'
    with pytest.raises(LavaError, match='No email handler for type bad-type'):
        Emailer.handler(conn_spec, realm='test', sender=sender)


# ------------------------------------------------------------------------------
def test_emailer_conn_disabled(aws_account_id):
    """Test with SES email handler."""
    conn_spec = {
        'conn_id': 'test',
        'enabled': False,
        'type': 'email',
        "configuration_set": 'lava-test',
    }

    sender = 'from@example.com'
    with pytest.raises(LavaError, match='not enabled'):
        Emailer.handler(conn_spec, realm='test', sender=sender)


# ------------------------------------------------------------------------------
def test_smtp_emailer_ok(td):
    """Test with SMTP email handler."""

    # Mailpit in the container
    conn_spec = {
        'conn_id': 'test',
        'type': 'smtp',
        'host': MAILPIT_HOST,
        'port': MAILPIT_SMTP_PORT,
        'user': 'lava',
        # SSM parameter name - not password value
        'password': '/lava/test/smtp_local/lava/password',
        'enabled': True,
    }

    msg_id = str(uuid4())
    sender = 'from@example.com'
    to = ['to_1@example.com', 'to_2@example.com']
    attachments = [
        EmailAttachment('att1.txt', 'Attachment 1'),
        str(td / 'f1.txt'),
    ]
    with Emailer.handler(conn_spec, realm='test', sender=sender) as emailer:
        emailer.send(
            subject=msg_id,
            message=f'Test message: {msg_id}',
            to=to,
            reply_to='reply@example.com',
            attachments=attachments,
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
def test_smtp_emailer_no_sender():

    # Mailpit in the container
    conn_spec = {
        'conn_id': 'test',
        'type': 'smtp',
        'host': MAILPIT_HOST,
        'port': MAILPIT_SMTP_PORT,
        'user': 'lava',
        # SSM parameter name - not password value
        'password': '/lava/test/smtp_local/lava/password',
        'enabled': True,
    }

    to = 'to@example.com'
    msg_id = str(uuid4())
    with pytest.raises(LavaError, match='Email sender must be specified'):
        with Emailer.handler(conn_spec, realm='test') as emailer:
            emailer.send(subject=msg_id, message=f'Test message: {msg_id}', to=to)


# ------------------------------------------------------------------------------
def test_smtp_emailer_no_recipient():

    # Mailpit in the container
    conn_spec = {
        'conn_id': 'test',
        'type': 'smtp',
        'host': MAILPIT_HOST,
        'port': MAILPIT_SMTP_PORT,
        'user': 'lava',
        'from': 'from@example.com',
        # SSM parameter name - not password value
        'password': '/lava/test/smtp_local/lava/password',
        'enabled': True,
    }

    msg_id = str(uuid4())
    with pytest.raises(LavaError, match='No recipients specified'):
        with Emailer.handler(conn_spec, realm='test') as emailer:
            emailer.send(subject=msg_id, message=f'Test message: {msg_id}')


# ------------------------------------------------------------------------------
def test_smtp_emailer_no_subject():

    # Mailpit in the container
    conn_spec = {
        'conn_id': 'test',
        'type': 'smtp',
        'host': MAILPIT_HOST,
        'port': MAILPIT_SMTP_PORT,
        'user': 'lava',
        'from': 'from@example.com',
        # SSM parameter name - not password value
        'password': '/lava/test/smtp_local/lava/password',
        'enabled': True,
    }

    msg_id = str(uuid4())
    with pytest.raises(LavaError, match='subject and message must be specified'):
        with Emailer.handler(conn_spec, realm='test') as emailer:
            emailer.send(subject='', message=f'Test message: {msg_id}', to='to@example.com')


# ------------------------------------------------------------------------------
@pytest.mark.parametrize(
    'addresses, exc_type, error_message',
    [
        ({'a'}, TypeError, 'Email addresses must be a string or list of strings'),
        ([{'a'}], TypeError, 'Email address entries must be strings'),
        ('x@', ValueError, 'Bad email address: x@'),
        (['ok@example.com', 'x@'], ValueError, 'Bad email address: x@'),
    ],
)
def test_build_address_header_fail(addresses, exc_type, error_message):
    """Test with SES email handler."""
    with pytest.raises(exc_type, match=error_message):
        build_address_header(addresses)  # noqa
