"""Checker for the inline/ok foreach job."""

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
        """Checker for the partial-fail-stop foreach job."""

        assert job_result is None
        assert job_error

        child_job_id = self.job_spec['payload']
        # job_events should contain results for both the foreach parent job and
        # the child job.
        assert set(job_events) == {
            (self.job_id, self.run_id),
            (child_job_id, self.run_id),
        }, 'job events count'

        # Validate the summary of successes / failures
        job_run_info = job_events[self.job_id, self.run_id][-1]['info']
        error_data = job_run_info['error_data']
        assert error_data['exit_status'] == 1, 'exit status'
        assert error_data['failed_indexes'] == [1], 'failed indexes'
        assert error_data['jobs_completed'] == 1

        # ------------------------------
        # Now check the child job runs
        child_events = job_events[child_job_id, self.run_id]

        # Should be a starting / running / complete|failed entry for each child run
        child_completed_events = [d for d in child_events if d['status'] == 'complete']
        child_failed_events = [d for d in child_events if d['status'] == 'failed']
        assert len(child_completed_events) == 1
        assert len(child_failed_events) == 1
