"""
Custom job checker.

WARNING: This is a very basic success / fail check. It doesn't check if a
         message was sent or what it contains. Lot of fiddling to do this in
         Ministack.
"""

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

        # Just check we didn't get "action_failed"
        assert job_events[self.job_id, self.run_id][-1]['status'] == 'complete'
