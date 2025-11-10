"""
Provides lava based support for sending messages to Slack.

It defines a handler class for Slack connectivity.

"""

from __future__ import annotations

import json
import logging
import time
from typing import Any

import requests

__author__ = 'Murray Andrews'

DEFAULT_COLOUR = '#bbbbbb'
MAX_SUBJECT_LEN = 250
MAX_MESSAGE_LEN = 3000
REQUESTS_TIMEOUT = 10


# ------------------------------------------------------------------------------
class Slack:
    """
    Handler class for Slack webhook connections.

    :param conn_spec:   A database connection specification.
    :param realm:       Lava realm.
    :param sender:      Default sender. If not specified, the `from` key in
                        the conn_spec is used if present.
    :param style:       Default display style for the Slack message. Options
                        are `block` (default), `attachment` and `plain`.
    :param colour:      Default colour for the sidebar for Slack messages
                        sent using `attachment` style. This can be any hex
                        colour code or one of the Slack special values
                        `good`, `warning` or `danger`.
    :param preamble:    Default preamble at the start of the message.
                        Useful values include things such as `<!here>` and
                        `<!channel>` which will cause Slack to insert `@here`
                        and `@channel` alert tags respectively.
    :param logger:      A logger. If not specified, use the root logger.

    """

    STYLES = {'block', 'attachment', 'plain'}
    STYLE_DEFAULT = 'block'

    # --------------------------------------------------------------------------
    def __init__(
        self,
        conn_spec: dict[str, Any],
        realm: str,
        sender: str = None,
        style: str = None,
        colour: str = None,
        preamble: str = None,
        logger: logging.Logger = None,
    ):
        """Create a Slack handler instance."""

        if not conn_spec.get('enabled'):
            raise Exception(f'Connection "{conn_spec["conn_id"]}" is not enabled')

        if conn_spec.get('type') != 'slack':
            raise ValueError(f'Connection "{conn_spec["conn_id"]}" is not a slack connection')

        self.conn_spec = conn_spec
        self.realm = realm
        self.sender = sender if sender else conn_spec.get('from', f'lava@{realm}')
        self.colour = colour if colour else conn_spec.get('colour', DEFAULT_COLOUR)
        self.style = style if style else conn_spec.get('style', self.STYLE_DEFAULT)
        self.preamble = preamble if preamble else conn_spec.get('preamble')
        self.logger = logger if logger else logging.getLogger()

        if self.style not in self.STYLES:
            raise ValueError(f'Connection "{conn_spec["conn_id"]}": Bad style {style}')

    # --------------------------------------------------------------------------
    def send(
        self,
        message: str,
        subject: str = None,
        preamble: str = None,
        sender: str = None,
        style=None,
        colour: str = None,
    ) -> None:
        """
        Send a formatted message to a slack channel.

        :param message:     Message body. Must not be empty.
        :param subject:     Message subject. Optional.
        :param preamble:    An optional preamble at the start of the message.
                            Useful values include things such as <!here> and
                            <!channel> which will cause Slack to insert @here
                            and @channel alert tags respectively.
        :param sender:      Sender name.
        :param style:       Display style for the Slack message. Options are
                            `block` (default), `attachment` and `plain`.
        :param colour:      Colour for the sidebar for Slack messages
                            sent using 'attachment' style. This can be any hex
                            colour code or one of the Slack special values
                            `good`, `warning` or `danger`.
        """

        if not message:
            raise ValueError('Cannot send slack message: message must be specified')

        if not style:
            style = self.style
        if not sender:
            sender = self.sender
        if not preamble:
            preamble = self.preamble
        if not colour:
            colour = self.colour
        if not colour.startswith('#'):
            colour = f'#{colour}'

        if subject:
            subject = subject[:MAX_SUBJECT_LEN]

        message = message[:MAX_MESSAGE_LEN]

        ts = int(time.time())

        plain_msg = [
            preamble,
            f'*{sender}*:' if sender else None,
            f'*{subject}*:' if subject else None,
            message,
        ]

        if style == 'block':
            header = [
                preamble,
                f'*From*: {sender}' if sender else None,
                f'*Subject*: {subject}' if subject else None,
            ]
            slack_msg = {
                'text': ' '.join([s for s in plain_msg if s]),
                'blocks': [
                    {
                        'type': 'section',
                        'text': {'type': 'mrkdwn', 'text': '\n'.join([s for s in header if s])},
                    },
                    {'type': 'divider'},
                    {'type': 'section', 'text': {'type': 'mrkdwn', 'text': message}},
                    {
                        'type': 'context',
                        'elements': [
                            {
                                'type': 'mrkdwn',
                                'text': f'Event time: <!date^{ts}^{{date_short_pretty}}'
                                f' at {{time}}| >',
                            }
                        ],
                    },
                ],
            }
        elif style == 'attachment':
            slack_msg = {
                'attachments': [
                    {
                        'fallback': message,
                        'author_name': sender if sender else self.sender,
                        'color': colour if colour else self.colour,
                        'text': message,
                        'footer': 'Event time',
                        'ts': ts,
                    }
                ]
            }
            if subject:
                slack_msg['attachments'][0]['title'] = subject

            if preamble:
                slack_msg['text'] = preamble

        elif style == 'plain':
            slack_msg = {'text': ' '.join([s for s in plain_msg if s])}
        else:
            raise ValueError(f'Bad slack message style: {style}')

        self.send_raw(slack_msg)

    # --------------------------------------------------------------------------
    def send_raw(self, slack_msg: dict[str, Any]) -> None:
        """
        Send a raw message to a slack channel.

        See https://api.slack.com/messaging/webhooks

        :param slack_msg:   A Slack message payload. The message structure must
                            conform to the format required by the Slack webhook
                            API.
        """

        response = requests.post(
            self.conn_spec['webhook_url'],
            data=json.dumps(slack_msg),
            headers={'Content-Type': 'application/json'},
            timeout=REQUESTS_TIMEOUT,
        )
        if not response.ok:
            raise Exception(f'Slack response {response.status_code} - {response.text}')

        self.logger.debug(f'Slack message sent to {self.conn_spec["webhook_url"]}')
