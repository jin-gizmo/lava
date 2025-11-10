"""
Lava based support for outbound email.

It defines a base class for email sending. Concrete classes use real email
sending services (e.g. AWS SES).

Alway use the base class, which is also a context manager. Typical use of the base
class is:

```python
from lava.lib.email import Emailer

with h as Emailer.handler(conn_spec, realm, sender) as h:
    h.send(to='x@y.com', subject='Hello world', message='Yahoo')
```

"""

from __future__ import annotations

import logging
import os
import smtplib
from collections.abc import Callable, Iterable
from contextlib import suppress
from dataclasses import dataclass
from email.message import EmailMessage
from mimetypes import guess_type
from typing import Any

import boto3
from botocore.exceptions import ClientError
from smart_open import open  # noqa A004

from .aws import ses_send, ssm_get_param
from .misc import dict_check, is_html, listify, size_to_bytes, str2bool
from ..config import config, config_load
from ..lavacore import LavaError

__author__ = 'Murray Andrews'


# ------------------------------------------------------------------------------
def content_type(filename: str) -> tuple[str, str]:
    """
    Try to guess the content type based on filename suffix.

    :param filename:    File name.
    :return:            (maintype, subtype) or a generic default.

    """

    ctype, encoding = guess_type(filename)
    if ctype is None or encoding is not None:
        return 'application', 'octet-stream'
    maintype, subtype = ctype.split('/')
    return maintype, subtype


# ------------------------------------------------------------------------------
@dataclass
class EmailAttachment:
    """For in-memory attachments."""

    name: str
    data: str | bytes


# ------------------------------------------------------------------------------
class Emailer:
    """
    Abstract base class for an outbound email handler.

    This is not a generic model but rather a specific adaptation for the
    purposes of lava.

    This is a context manager and can be used thus:

    ```python
        with h as Emailer.handler(conn_spec, realm, sender) as h:
            h.send(to='x@y.com', subject='Hello world', message='Yahoo')
    ```

    :param conn_spec:   A database connection specification.
    :param realm:       Lava realm.
    :param sender:      Default sender. If not specified, the `from` key in
                        the conn_spec is used if present. Otherwise each
                        handler has to work this out for itself.
    :param aws_session: A boto3 Session(). If not specified a default will
                        be created if required. Default None.
    :param logger:      A logger. If not specified, use the root logger.

    """

    _EMAIL_HANDLERS = {}

    # --------------------------------------------------------------------------
    @classmethod
    def register(cls, *args: str) -> Callable:
        """
        Register email handler classes.

        Usage:

        ```python
        @Emailer.register(emailer_type1, ...)
        a_class(...)
        ```

        :param args:        A list of email subsystem types that the decorated class
                            handles. These will correspond to the type/subtype fields
                            in the conn_spec.
        """

        def decorate(handler_cls: type) -> type:
            """
            Register the handler cls.

            :param handler_cls: Class to register.
            :return:            Unmodified class.

            """
            for emailer_type in args:
                if emailer_type in cls._EMAIL_HANDLERS:
                    raise LavaError(f'{emailer_type} is already registered')
                cls._EMAIL_HANDLERS[emailer_type] = handler_cls
            return handler_cls

        return decorate

    # --------------------------------------------------------------------------
    @classmethod
    def handler(cls, conn_spec: dict[str, Any], *args, **kwargs) -> Emailer:
        """
        Create a handler for the specified emailer type.

        The appropriate handler is selected by looking at the `type` and
        `subtype` elements of the connection spec.

        If the `type` matches a registered handler, that will be used.

        If `type` is `email`, then the `subtype` is used to find a handler.

        If `type` is `email`, and no `subtype` is specified, AWS SES is used.
        (This is a legacy of the email connection handler in lava).

        Otherwise an exception is raised.

        :param conn_spec:   Lava connection spec. The handler required is
                            determined from the type field.

        :return:            An emailer handler.
        """

        with suppress(KeyError):
            return cls._EMAIL_HANDLERS[conn_spec['type']](conn_spec, *args, **kwargs)

        # Try for a subtype handler
        if conn_spec['type'] == 'email':
            if 'subtype' in conn_spec:
                try:
                    return cls._EMAIL_HANDLERS[conn_spec['subtype']](conn_spec, *args, **kwargs)
                except KeyError:
                    raise LavaError(
                        'No email handler for type/subtype'
                        f' {conn_spec["type"]}/{conn_spec["subtype"]}'
                    )
            else:
                # Default for email type with no subtype is ses
                return cls._EMAIL_HANDLERS['ses'](conn_spec, *args, **kwargs)

        raise LavaError(f'No email handler for type {conn_spec["type"]}')

    # --------------------------------------------------------------------------
    def __init__(
        self,
        conn_spec: dict[str, Any],
        realm: str,
        sender: str = None,
        aws_session: boto3.Session = None,
        logger: logging.Logger = None,
    ):
        """Create an Emailer instamnce."""

        if not conn_spec.get('enabled'):
            raise LavaError(f'Connection "{conn_spec["conn_id"]}" is not enabled')
        self.conn_spec = conn_spec
        self.realm = realm
        self.aws_session = aws_session or boto3.Session()
        self.sender = sender or conn_spec.get('from')
        self.logger = logger or logging.getLogger()

        # We need some config variables from the realms table. Normally the lava
        # worker loads all this but if we are using this as a standalone module
        # we need to make sure the realms table has been read.
        config_load(self.realm, aws_session=self.aws_session)

    # --------------------------------------------------------------------------
    def __enter__(self) -> Emailer:
        """Context manager open."""

        self.logger.debug('Entering context for Emailer: %s', self.conn_spec['type'])
        return self

    # --------------------------------------------------------------------------
    def __exit__(self, *args, **kwargs):
        """Context manager exit."""

        self.logger.debug('Exiting context for Emailer: %s', self.conn_spec['type'])
        self.close()

    # --------------------------------------------------------------------------
    def message(
        self,
        subject: str,
        message: str,
        to: Iterable[str] | str = None,
        cc: Iterable[str] | str = None,
        sender: str = None,
        reply_to: Iterable[str] | str = None,
        attachments: Iterable[EmailAttachment | str] = None,
    ) -> EmailMessage:
        """
        Construct an email message.

        :param subject:     Message subject. Must not be empty.
        :param message:     Message body. Must not be empty. If it looks like
                            HTML some handlers will treat it differently.
        :param to:          Recipient address or iterable of addresses.
        :param cc:          Cc address or iterable of addresses.
        :param sender:      Default From address.
        :param reply_to:    Default Reply-To address.
        :param attachments: An iterable of either filenames to attach or in-memory
                            attachments.
        :return:            The message.
        """

        if not sender:
            raise LavaError('Email sender must be specified')

        if not any((to, cc)):
            raise LavaError('No recipients specified for email')

        if not subject or not message:
            raise LavaError('Cannot send email: subject and message must be specified')

        msg = EmailMessage()

        msg['From'] = sender
        msg['Subject'] = subject

        # Add destination addresses. Note that we deliberately do not include Bcc.
        for hdr, val in zip(['To', 'Cc', 'Reply-To'], [to, cc, reply_to]):
            if val:
                msg[hdr] = val

        msg.set_content(message, subtype='html' if is_html(message) else 'plain')

        self.logger.debug('Message (without attachments): %s', msg.as_string())

        # ------------------------------
        # Attachments

        max_attachment_size = config('EMAIL_MAX_ATTACHMENT_SIZE', size_to_bytes)
        max_attachments = config('EMAIL_MAX_ATTACHMENTS', int)
        if len(attachments := tuple(attachments or [])) > max_attachments:
            raise LavaError(f'Too many email attachments (max {max_attachments})')

        data, name, maintype, subtype = None, None, None, None
        for n, a in enumerate(attachments, 1):
            if isinstance(a, EmailAttachment):
                data, name = a.data, a.name
                if len(data) > max_attachment_size:
                    raise LavaError(f'Attachment {name} exceeds (max {max_attachment_size} bytes')
                maintype, subtype = content_type(a.name)
            elif isinstance(a, str):
                with open(
                    a, 'rb', transport_params={'client': self.aws_session.client('s3')}
                ) as fp:
                    # As the attachment could be in S3 we use seek to get the size
                    # before we load it into mem.
                    if fp.seek(0, 2) > max_attachment_size:
                        raise LavaError(f'Attachment {a} exceeds {max_attachment_size} bytes')
                    fp.seek(0)
                    data, name = fp.read(), os.path.basename(a)
                    maintype, subtype = content_type(a)
            else:
                raise ValueError(f'Bad type for attachment {n}: {type(a)}')

            msg.add_attachment(data, maintype=maintype, subtype=subtype, filename=name)

        return msg

    # --------------------------------------------------------------------------
    def send(
        self,
        subject: str,
        message: str,
        to: Iterable[str] | str = None,
        cc: Iterable[str] | str = None,
        bcc: Iterable[str] | str = None,
        sender: str = None,
        reply_to: Iterable[str] | str = None,
        attachments: Iterable[EmailAttachment | str] = None,
    ) -> None:
        """
        Send an email.

        :param subject:     Message subject. Must not be empty.
        :param message:     Message body. Must not be empty. If it looks like
                            HTML some handlers will treat it differently.
        :param to:          Recipient address or iterable of addresses.
        :param cc:          Cc address or iterable of addresses.
        :param bcc:         Bcc address or iterable of addresses.
        :param sender:      Default From address.
        :param reply_to:    Default Reply-To address.
        :param attachments: An iterable of either filenames to attach or in-memory
                            attachments.

        """

        raise NotImplementedError('send')

    # --------------------------------------------------------------------------
    # noinspection PyMethodMayBeStatic
    def close(self) -> None:
        """Close the connection."""

        pass


# ------------------------------------------------------------------------------
# This is the old SES email implementation that used SendEmail not SendRawEmail.
class AwsSesLegacy(Emailer):
    """Email sender implementation using AWS SES."""

    # --------------------------------------------------------------------------
    def __init__(self, *args, **kwargs):
        """See super class."""

        super().__init__(*args, **kwargs)

        # We need some config variables from the realms table. Normally the lava
        # worker loads all this but if we are using this as a standalone module
        # we need to make sure the realms table has been read.
        config_load(self.realm, aws_session=self.aws_session)

        # If sender not specified we need to get the default from the realm
        if not self.sender:
            self.sender = self.conn_spec.get('from', config('SES_FROM'))

    # --------------------------------------------------------------------------
    def send(
        self,
        subject: str,
        message: str,
        to: Iterable[str] | str = None,
        cc: Iterable[str] | str = None,
        bcc: Iterable[str] | str = None,
        sender: str = None,
        reply_to: Iterable[str] | str = None,
        attachments: Iterable[EmailAttachment | str] = None,
    ) -> None:
        """
        Send an email using SES.

        :param subject:     Message subject. Must not be empty.
        :param message:     Message body. Must not be empty. If it looks like
                            HTML some handlers will treat it differently.
        :param to:          Recipient address or iterable of addresses.
        :param cc:          Cc address or iterable of addresses.
        :param bcc:         Bcc address or iterable of addresses.
        :param sender:      Default From address.
        :param reply_to:    Default Reply-To address.
        :param attachments: An iterable of either filenames to attach or in-memory
                            attachments.

        """

        if not subject or not message:
            raise ValueError('Cannot send email: subject and message must be specified')

        if attachments:
            raise LavaError(f'{self.__class__.__name__} does not support attachments')

        if not sender:
            sender = self.sender
        if not sender:
            raise LavaError('Sender must be specified')

        html, text = (message, None) if is_html(message) else (None, message)

        ses_send(
            sender=sender,
            to=to,
            cc=cc,
            bcc=bcc,
            reply_to=reply_to if reply_to else self.conn_spec.get('reply_to'),
            subject=subject,
            message=text,
            html=html,
            region=self.conn_spec.get('region', config('SES_REGION')),
            config_set=self.conn_spec.get('configuration_set', config('SES_CONFIGURATION_SET')),
            aws_session=self.aws_session,
        )


# ------------------------------------------------------------------------------
@Emailer.register('ses')
class AwsSes(Emailer):
    """Email sender implementation using AWS SES."""

    # --------------------------------------------------------------------------
    def __init__(
        self,
        conn_spec: dict[str, Any],
        realm: str,
        sender: str = None,
        aws_session: boto3.Session = None,
        logger: logging.Logger = None,
    ):
        """Create an Emailer instamnce."""

        super().__init__(conn_spec, realm, sender=sender, aws_session=aws_session, logger=logger)
        self.ses_client = self.aws_session.client(
            'ses', region_name=self.conn_spec.get('region', config('SES_REGION'))
        )

    # --------------------------------------------------------------------------
    def send(
        self,
        subject: str,
        message: str,
        to: Iterable[str] | str = None,
        cc: Iterable[str] | str = None,
        bcc: Iterable[str] | str = None,
        sender: str = None,
        reply_to: Iterable[str] | str = None,
        attachments: Iterable[EmailAttachment | str] = None,
    ) -> None:
        """
        Send an email using SES.

        :param subject:     Message subject. Must not be empty.
        :param message:     Message body. Must not be empty. If it looks like
                            HTML some handlers will treat it differently.
        :param to:          Recipient address or iterable of addresses.
        :param cc:          Cc address or iterable of addresses.
        :param bcc:         Bcc address or iterable of addresses.
        :param sender:      Default From address.
        :param reply_to:    Default Reply-To address.
        :param attachments: An iterable of either filenames to attach or in-memory
                            attachments.

        """

        msg_bytes = self.message(
            subject=subject,
            message=message,
            to=to,
            cc=cc,
            sender=sender or self.sender or config('SES_FROM'),
            reply_to=reply_to,
            attachments=attachments,
        ).as_bytes()

        max_email_size = config('EMAIL_MAX_SIZE', size_to_bytes)
        if len(msg_bytes) > max_email_size:
            raise ValueError(
                f'Email size {len(msg_bytes)} bytes exceeds maximum allowed size'
                f' of {max_email_size} bytes'
            )

        send_args = {
            'Destinations': [
                *(listify(to) if to else []),
                *(listify(cc) if cc else []),
                *(listify(bcc) if bcc else []),
            ],
            'RawMessage': {'Data': msg_bytes},
        }
        config_set = self.conn_spec.get('configuration_set', config('SES_CONFIGURATION_SET'))
        if config_set:
            send_args['ConfigurationSetName'] = config_set

        try:
            response = self.ses_client.send_raw_email(**send_args)
        except ClientError as e:
            raise LavaError(f'{self.conn_spec["conn_id"]}: {e.response["Error"]["Message"]}')
        self.logger.debug('Email sent: message ID = %s', response['MessageId'])


# ------------------------------------------------------------------------------
@Emailer.register('smtp')
class SmtpTls(Emailer):
    """Email sender implementation using SMTP. Includes support for TLS."""

    CONNECTION_REQUIRED_FIELDS = {'host'}
    SMTP_TLS_TIMEOUT = 10  # Connect timeout in seconds
    DEBUG_LEVEL = 0  # Set to 0 (off), 1 or 2

    # --------------------------------------------------------------------------
    def __init__(self, *args, **kwargs):
        """See super class."""

        super().__init__(*args, **kwargs)

        conn_id = self.conn_spec['conn_id']

        # ----------------------------------------
        # Make sure the spec is ok
        try:
            dict_check(self.conn_spec, required=self.CONNECTION_REQUIRED_FIELDS)
        except ValueError as e:
            raise LavaError(f'{conn_id}: Bad connection record: {e}')

        # ----------------------------------------
        # Get connection details
        tls = str2bool(self.conn_spec.get('tls', False))
        host = self.conn_spec['host']
        port = int(self.conn_spec.get('port', smtplib.SMTP_SSL_PORT if tls else smtplib.SMTP_PORT))

        user = self.conn_spec.get('user')
        password = None
        if user:
            try:
                password = ssm_get_param(self.conn_spec['password'], aws_session=self.aws_session)
            except KeyError:
                raise LavaError(f'{conn_id}: password is required if user is specified')
            except LavaError as e:
                raise LavaError(f'{conn_id}: {e}')

        # ----------------------------------------
        # Login
        try:
            self.logger.debug(f'{conn_id}: Connecting to {host}')
            self.server = smtplib.SMTP(host, port, timeout=self.SMTP_TLS_TIMEOUT)
            self.server.set_debuglevel(self.DEBUG_LEVEL)
            self.logger.debug(f'{conn_id}: Connected: {self.server}')

            response = self.server.ehlo()
            self.logger.debug(f'{conn_id}: EHLO response: {response}')

            if tls:
                self.logger.debug(f'{conn_id}: Starting TLS')
                self.server.starttls()

            if user:
                self.logger.debug(f'{conn_id}: Logging in as {user}')
                self.server.login(user, password)
                self.logger.debug(f'{conn_id}: Logged in')
        except LavaError as e:
            raise LavaError(f'{conn_id}: {e}')

    # --------------------------------------------------------------------------
    def send(
        self,
        subject: str,
        message: str,
        to: Iterable[str] | str = None,
        cc: Iterable[str] | str = None,
        bcc: Iterable[str] | str = None,
        sender: str = None,
        reply_to: Iterable[str] | str = None,
        attachments: Iterable[EmailAttachment | str] = None,
    ) -> None:
        """
        Send an email via SMTP.

        :param subject:     Message subject. Must not be empty.
        :param message:     Message body. Must not be empty. If it looks like
                            HTML some handlers will treat it differently.
        :param to:          Recipient address or iterable of addresses.
        :param cc:          Cc address or iterable of addresses.
        :param bcc:         Bcc address or iterable of addresses.
        :param sender:      Default From address.
        :param reply_to:    Default Reply-To address.
        :param attachments: An iterable of either filenames to attach or in-memory
                            attachments.

        """

        msg = self.message(
            subject=subject,
            message=message,
            to=to,
            cc=cc,
            sender=sender or self.sender,
            reply_to=reply_to,
            attachments=attachments,
        )

        max_email_size = config('EMAIL_MAX_SIZE', size_to_bytes)
        if (email_size := len(msg.as_bytes())) > max_email_size:
            raise ValueError(
                f'Email size {email_size} bytes exceeds maximum allowed size'
                f' of {max_email_size} bytes'
            )

        try:
            response = self.server.send_message(msg)
        except LavaError as e:
            raise LavaError(f'{self.conn_spec["conn_id"]}: {e}')

        self.logger.debug('Message sent: %s', response)

    # --------------------------------------------------------------------------
    def close(self) -> None:
        """Close the connection."""

        self.server.quit()
