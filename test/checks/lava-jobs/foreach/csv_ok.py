"""Checker for the csv/ok foreach job."""

from __future__ import annotations

from typing import Any

from lava import LavaError
from test.conftest import S3path
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
        """Check function for lava-jobs/foreach/csv-ok job."""

        assert job_result is not None, 'job_result is None'
        assert job_result['exit_status'] == 0, f'exit status = {job_result["exit_status"]}'
        assert job_error is None, 'job_error is not None'

        child_job_id = self.job_spec['payload']
        # job_events should contain results for both the foreach parent job and
        # the child job.
        assert set(job_events) == {
            (self.job_id, self.run_id),
            (child_job_id, self.run_id),
        }, 'job events count'

        # Get the CSV source data driving the foreach.
        # This filename will be fully jinja rendered by this point
        foreach_file = self.job_spec['parameters']['foreach']['filename']
        foreach_data = S3path(foreach_file).read().splitlines()

        # Validate the summary of successes / failures
        job_run_info = job_events[self.job_id, self.run_id][-1]['info']
        assert job_run_info['exit_status'] == 0, 'exit status'
        assert not job_run_info['failed_indexes'], 'failed indexes'
        assert job_run_info['foreach_len'] == len(foreach_data) - 1, 'foreach_len'
        assert job_run_info['jobs_completed'] == len(foreach_data) - 1, 'jobs_completed'

        # ------------------------------
        # Now check the child job runs
        child_events = job_events[child_job_id, self.run_id]

        # Should be a starting / running / complete entry for each child run
        child_completed_events = [d for d in child_events if d['status'] == 'complete']
        assert len(child_completed_events) == len(foreach_data) - 1, 'Child jobs event count'
        # Make sure the globals from the parent propagated through to the child job output
        for child_event_info in child_completed_events:
            output = S3path(child_event_info['info']['output'][0]['stdout']).read().decode('utf8')
            for gk, gv in self.job_spec['globals'].items():
                # Skip the lava internal globals
                if gk.startswith('lava'):
                    continue
                assert f'{gk}={gv}\n' in output, f'{gk}={gv} not in output'
