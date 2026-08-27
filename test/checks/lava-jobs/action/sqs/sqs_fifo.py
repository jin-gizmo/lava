"""Custom job checker."""

from __future__ import annotations

from typing import Any
from uuid import uuid4

import boto3

from lava import LavaError
from test.integration.conftest import HandlerChecker


# ------------------------------------------------------------------------------
class Checker(HandlerChecker):
    """Custom checker."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.queue_name = f'{uuid4()}.fifo'
        self.sqs = boto3.client('sqs')
        self.queue_url = None

    def setup(self) -> None:
        """Setup."""

        self.queue_url = self.sqs.create_queue(QueueName=self.queue_name)['QueueUrl']
        for action in self.job_spec['on_success']:
            action['queue'] = self.queue_name

    def check(
        self,
        job_result: dict[str, Any] | None,
        job_events: dict[tuple[str, str], list[dict[str, Any]]],
        job_error: LavaError | None,
    ) -> None:
        """Custom checker."""

        assert job_events[self.job_id, self.run_id][-1]['status'] == 'complete'

        messages = self.sqs.receive_message(QueueUrl=self.queue_url, MaxNumberOfMessages=10)[
            'Messages'
        ]
        assert len(messages) == 1
        assert messages[0]['Body'] == self.run_id

    def teardown(self) -> None:
        """Teardown."""
        self.sqs.delete_queue(QueueUrl=self.queue_url)
