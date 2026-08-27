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

        assert job_result
        assert not job_error

        assert job_result['exit_status'] == 0
        assert job_result['failed_indexes'] == [1]
        assert job_result['jobs_completed'] == job_result['foreach_len'] - len(
            job_result['failed_indexes']
        )

        child_job_id = self.job_spec['payload']
        # job_events should contain results for both the foreach parent job and
        # the child job.
        assert set(job_events) == {
            (self.job_id, self.run_id),
            (child_job_id, self.run_id),
        }, 'job events count'

        # ------------------------------
        # Check the child job runs
        child_events = job_events[child_job_id, self.run_id]

        # Should be a starting / running / complete|failed entry for each child run
        child_completed_events = [d for d in child_events if d['status'] == 'complete']
        child_failed_events = [d for d in child_events if d['status'] == 'failed']

        assert len(child_failed_events) == len(job_result['failed_indexes'])
        assert len(child_completed_events) == job_result['jobs_completed']
