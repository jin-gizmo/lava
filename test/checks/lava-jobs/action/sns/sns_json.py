"""Custom job checker."""

from __future__ import annotations

import json
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
        self.queue_name = str(uuid4())
        self.topic_name = self.queue_name
        self.sqs = boto3.client('sqs')
        self.sns = boto3.client('sns')
        self.queue_url = None
        self.topic_arn = None

    def setup(self) -> None:
        """Create an SNS topic with an SQS subscriber so we can grab messages."""

        sns = boto3.client('sns')
        self.queue_url = self.sqs.create_queue(QueueName=self.queue_name)['QueueUrl']
        queue_arn = self.sqs.get_queue_attributes(QueueUrl=self.queue_url)['Attributes']['QueueArn']
        self.topic_arn = self.sns.create_topic(Name=self.queue_name)['TopicArn']
        sns.subscribe(
            TopicArn=self.topic_arn,
            Protocol='sqs',
            Endpoint=queue_arn,
            Attributes={'RawMessageDelivery': 'true'},
        )

        self.job_spec['on_success'][0]['topic'] = self.topic_arn

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
        msg = json.loads(messages[0]['Body'])
        assert msg['Job'] == self.job_id
        assert msg['Run ID'] == self.run_id

    def teardown(self) -> None:
        """Teardown."""
        self.sqs.delete_queue(QueueUrl=self.queue_url)
        self.sns.delete_topic(TopicArn=self.topic_arn)
