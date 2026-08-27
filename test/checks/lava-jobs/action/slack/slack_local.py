"""Custom job checker."""

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

        assert job_events[self.job_id, self.run_id][-1]['status'] == 'complete'
        messages = self.fx.slack_emulator_client.search_conversation('general', self.run_id)
        assert len(messages) == 1
