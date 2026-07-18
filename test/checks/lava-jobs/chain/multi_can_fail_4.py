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
            - <{ prefix.job }>/exe/exit-123
            - <{ prefix.job }>/exe/exit-123
            - <{ prefix.job }>/exe/exit-123

        But they are all allowed to fail so the parent should succeed.
        """

        # The parent will succeed despite child failures
        assert job_result is not None
        assert job_result['exit_status'] == 0
        assert job_error is None

        # All 3 (identical) child jobs are expected to fail
        assert job_result['failed_jobs'] == self.job_spec['payload']
        assert job_result['jobs'] == []

        child_job_ids = set(self.job_spec['payload'])
        # We should have a event log trace for the parent and each unique child job name
        assert {x[0] for x in job_events} == child_job_ids | {self.job_id}, 'Event records'
        # The should all have the same run ID, irrespective of job_id
        assert all(x[1] == self.run_id for x in job_events), 'Common run IDs'

        # The event log for the parent is not very interesting. Should be the
        # standard starting/running/complete sequence.
        assert [ev['status'] for ev in job_events[self.job_id, self.run_id]] == [
            'starting',
            'running',
            'complete',
        ]

        # The failed second job is more interesting
        failed_job_id = job_result['failed_jobs'][0]
        failed_job_events = job_events[failed_job_id, self.run_id]

        assert [ev['status'] for ev in failed_job_events] == [
            'starting',
            'running',
            'failed',
        ] * len(job_result['failed_jobs']), 'ok child job statuses'
