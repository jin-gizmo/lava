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
        """
        Custom checker.

        The payload looks like this:
            - <{ prefix.job }>/cmd/hello-world
            - <{ prefix.job }>/exe/exit-123
            - <{ prefix.job }>/cmd/hello-world

        As no failures are allowed the third job will not be reached.
        """

        # The parent will fail due to child failure
        assert job_result is None
        assert isinstance(job_error, LavaError)

        # This job has 3 children and the second one will fail
        final_parent_event = job_events[self.job_id, self.run_id][-1]
        assert final_parent_event['status'] == 'failed'

        failed_job_id = self.job_spec['payload'][1]  # At least we expect so
        final_parent_info = final_parent_event['info']
        assert final_parent_info['error_data']['failed_jobs'] == [failed_job_id]
