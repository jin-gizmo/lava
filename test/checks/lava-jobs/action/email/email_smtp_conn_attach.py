"""Custom job checker."""

from __future__ import annotations

import json
from typing import Any
from urllib.request import urlopen

from const import MAILPIT_ADMIN_PORT, MAILPIT_HOST
from lava import LavaError
from test.integration.conftest import HandlerChecker


# ------------------------------------------------------------------------------
class Checker(HandlerChecker):
    """Custom checker."""

    def check(
        self,
        job_result: dict[str, Any] | None,
        job_events: dict[tuple[str, str], list[dict[str, Any]]],
        job_error: LavaError | None,
    ) -> None:
        """Custom checker."""

        assert job_events[self.job_id, self.run_id][-1]['status'] == 'complete'

        # Hit the Mailpit query endpoint to get a list of all email messages.
        # If you have more than 100,000 messages this will need pagination.

        email_admin_url = f'http://{MAILPIT_HOST}:{MAILPIT_ADMIN_PORT}/api/v1/messages?limit=100000'
        response = urlopen(email_admin_url)
        assert response.getcode() == 200

        to = [self.job_spec['on_success'][0]['to']]
        all_messages = json.loads(response.read())['messages']
        # ... find our message
        msg = [m for m in all_messages if m.get('Subject') == f'{self.job_id} {self.run_id}']
        assert len(msg) == 1
        assert {to['Address'] for to in msg[0]['To']} == set(to)
        assert msg[0]['Attachments'] == 1
