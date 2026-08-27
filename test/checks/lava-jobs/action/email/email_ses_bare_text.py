"""Custom job checker."""

from __future__ import annotations

import json
import os
from typing import Any
from urllib.request import urlopen

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

        # Hit the ministack email admin endpoint to get a list of all email messages
        email_admin_url = (
            f'{os.environ["AWS_ENDPOINT_URL"]}/_ministack/ses/messages?{self.fx.aws_account_id}'
        )
        response = urlopen(email_admin_url)
        assert response.getcode() == 200

        to = [self.job_spec['on_success'][0]['to']]
        all_messages = json.loads(response.read())['messages'][self.fx.aws_account_id]
        # ... find our message
        s = [m.get('Subject') for m in all_messages]
        msg = [m for m in all_messages if m.get('Subject') == f'{self.job_id} {self.run_id}']
        assert len(msg) == 1
        assert set(msg[0]['To']) == set(to)
