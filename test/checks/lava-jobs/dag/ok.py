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

        assert job_result
        assert not job_error

        assert job_result['exit_status'] == 0, 'exit status'
        assert not job_result['failed_jobs'], 'failed jobs'
        assert set(job_result['jobs']) == set(self.job_spec['payload'])

        # We should have a job events stream for the parent and each child
        assert len(job_events) == len(self.job_spec['payload']) + 1
        # And they should all be under the same run_id
        assert {x[1] for x in job_events} == {self.run_id}

        # Parent should be indicating success
        assert job_events[self.job_id, self.run_id][-1]['status'] == 'complete'

        # Child jobs should be indicating success
        for child_job_id in self.job_spec['payload']:
            assert job_events[child_job_id, self.run_id][-1]['status'] == 'complete'

        # Confirm that the jobs exevuted in the correct order
        # job_2 depends on job_1
        job_1 = 'test/cmd/sleep-2'
        job_2 = 'test/cmd/hello-world'

        assert job_result['jobs'] == [job_1, job_2]
        # Job 1 is a little sleep. Job 2 must start later than this one starts.
        assert (
                job_events[job_1, self.run_id][0]['ts_event']
                < job_events[job_2, self.run_id][0]['ts_event']
        )
        # Job 2 must not start before job 1 finishes
        assert (
            job_events[job_1, self.run_id][-1]['ts_event']
            <= job_events[job_2, self.run_id][0]['ts_event']
        )
