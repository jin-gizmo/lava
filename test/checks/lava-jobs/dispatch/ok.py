"""Custom checker."""

from __future__ import annotations

import json
from datetime import datetime
from typing import Any

import boto3
from lava import LavaError
from test.integration.conftest import HandlerChecker


# ------------------------------------------------------------------------------
class Checker(HandlerChecker):
    """Custom checker."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        """Init."""

        super().__init__(*args, **kwargs)
        self.sqs_messages: list[str] = []

    def setup(self) -> None:
        """
        Set up the checker.

        Because ministack does not expose a "peek" endpoint for SQS, we intercept
        the SQS send operation.
        """

        # noinspection PyUnusedLocal
        def sqs_send_msg_mock(
            msg: str, queue_name, delay: int = 0, aws_session: boto3.Session | None = None
        ) -> None:
            """Capture SQS messages."""
            self.sqs_messages.append(msg)

        self.fx.monkeypatch.setattr('lava.lavacore.sqs_send_msg', sqs_send_msg_mock)

    def check(
        self,
        job_result: dict[str, Any] | None,
        job_events: dict[tuple[str, str], list[dict[str, Any]]],
        job_error: LavaError | None,
    ) -> None:
        """Check function."""

        assert len(self.sqs_messages) == len(self.job_spec['payload'])
        job_prefix = self.job_spec.get('parameters', {}).get('job_prefix', '')

        parent_globals = {k: v for k, v in self.job_spec['globals'].items() if k != 'lava'}
        parent_params = self.job_spec.get('parameters', {}).get('parameters', {})

        for n, msg_s in enumerate(self.sqs_messages):
            msg = json.loads(msg_s)
            assert msg['realm'] == self.realm
            assert msg['job_id'] == job_prefix + self.job_spec['payload'][0]
            # Dispatch jobs get a unique run ID
            assert msg['run_id'] != self.run_id

            # The parent globals override the childs
            child_globals = {k: v for k, v in msg['globals'].items() if k != 'lava'}
            for k, v in parent_globals.items():
                assert child_globals[k] == v, f'Global {k}'

            # The parent parameters override the childs
            child_params = msg.get('parameters', {})
            for k, v in parent_params.items():
                assert child_params[k] == v, f'Parameter {k}'

            # Check the special lava globals
            assert msg['globals']['lava']['master_job_id'] == self.job_id
            assert msg['globals']['lava']['parent_job_id'] == self.job_id
            for k in ('master_start', 'master_ustart', 'parent_start', 'parent_ustart'):
                ts = self.job_spec['globals']['lava'][k]
                if isinstance(ts, datetime):
                    ts = ts.isoformat()
                assert msg['globals']['lava'][k] == ts, k
