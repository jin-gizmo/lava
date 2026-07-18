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
        """Check function."""

        failed_job = 'test/exe/exit-123'
        assert not job_result
        assert isinstance(job_error, LavaError)

        assert job_events[self.job_id, self.run_id][-1]['status'] == 'failed'
        assert job_events[self.job_id, self.run_id][-1]['info']['error_data']['failed_jobs'] == [
            failed_job
        ]

        assert job_events[failed_job, self.run_id][-1]['status'] == 'failed'
