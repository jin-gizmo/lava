"""Custom job checker."""

from __future__ import annotations

from typing import Any
from uuid import uuid4

import boto3

from lava import LavaError
from test.integration.conftest import HandlerChecker
import json


# ------------------------------------------------------------------------------
class Checker(HandlerChecker):
    """Custom checker."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.queue_name = str(uuid4())
        self.sqs = boto3.client('sqs')
        self.queue_url = None

    def setup(self) -> None:
        """Setup."""

        self.queue_url = self.sqs.create_queue(QueueName=self.queue_name)['QueueUrl']
        self.job_spec['on_success'][0]['queue'] = self.queue_name

    def check(
        self,
        job_result: dict[str, Any] | None,
        job_events: dict[tuple[str, str], list[dict[str, Any]]],
        job_error: LavaError | None,
    ) -> None:
        """Custom checker."""

        assert job_events[self.job_id, self.run_id][-1]['status'] == 'complete'

        messages = self.sqs.receive_message(QueueUrl=self.queue_url)['Messages']
        assert len(messages) == 1
        msg = json.loads(messages[0]['Body'])
        assert msg['Job'] == self.job_id
        assert msg['Run ID'] == self.run_id

    def teardown(self) -> None:
        """Teardown."""
        self.sqs.delete_queue(QueueUrl=self.queue_url)
