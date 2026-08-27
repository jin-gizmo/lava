"""Custom checker."""

from __future__ import annotations

from typing import Any

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

        assert job_result and job_result['exit_status'] == 0
        assert job_error is None

        # Custom log events have a "logging" status
        custom_log_events = [
            ev for ev in job_events[self.job_id, self.run_id] if ev['status'] == 'logging'
        ]
        assert len(custom_log_events) == 1
        assert custom_log_events[0]['info'] == {'alpha': 'Alpha', 'beta': 'Beta'}

        event = job_events[self.job_id, self.run_id][-1]
        assert event['status'] == 'complete'
