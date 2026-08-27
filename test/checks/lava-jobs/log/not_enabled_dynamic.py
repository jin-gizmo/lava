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

        assert not job_result
        assert job_error is None

        event = job_events[self.job_id, self.run_id][-1]
        assert event['info'] == 'Job not enabled (enabled="false")'
        assert event['status'] == 'skipped'
