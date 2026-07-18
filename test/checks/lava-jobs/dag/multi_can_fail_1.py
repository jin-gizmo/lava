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

        jobs = ['test/cmd/sleep-1', 'test/cmd/sleep-2', 'test/exe/exit-123']
        assert job_result
        assert not job_error

        assert job_result['exit_status'] == 0, 'exit status'
        assert job_result['jobs'] == jobs[0:-1]
        assert job_result['failed_jobs'] == [jobs[2]]

        # # We should have a job events stream for the parent and each child
        assert len(job_events) == len(jobs) + 1
        # And they should all be under the same run_id
        assert {x[1] for x in job_events} == {self.run_id}

        # Parent should be indicating success
        assert job_events[self.job_id, self.run_id][-1]['status'] == 'complete'

        # Child jobs should be indicating success
        for child_job_id in jobs[0:-1]:
            assert job_events[child_job_id, self.run_id][-1]['status'] == 'complete'

        # Final job is a fail
        assert job_events[jobs[-1], self.run_id][-1]['status'] == 'failed'
