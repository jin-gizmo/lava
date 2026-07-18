"""Assertions for the hello-world.yaml cmd job."""

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
        """Check function for lava-jobs/cmd/fail-retry job."""

        assert job_result is None
        assert str(job_error) == 'Failed with exit status 33'

        # Check the log shows our retries.
        # This job tries and fails 3 times. Our logs should contain status like this:
        expected_statuses = [
            'starting',
            'running',  # Attempt #1
            'retrying',
            'running',  # Attempt #2
            'retrying',
            'running',  # Attempt #3
            'failed',
        ]

        assert expected_statuses == [e['status'] for e in job_events[self.job_id, self.run_id]]

        # The output from the final run should contain this:
        expected_final_run_output = 'Iteration is 3\nIteration ENV var is 3\n'

        final_output_file = S3path(
            job_events[(self.job_id, self.run_id)][-1]['info']['error_data']['output'][0]['stdout']
        )
        assert final_output_file.read().decode('utf-8') == expected_final_run_output
