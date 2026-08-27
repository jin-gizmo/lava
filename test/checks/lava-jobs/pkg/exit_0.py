"""Custom checker."""

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
        """Check function for lava-jobs/pkg/exit-0 job."""

        assert job_result and job_result['exit_status'] == 0
        assert not job_error

        assert job_events[self.job_id, self.run_id][-1]['info']['exit_status'] == 0

        stderr_filename = job_events[self.job_id, self.run_id][-1]['info']['output'][0]['stderr']
        stderr = S3path(stderr_filename).read().decode('utf-8')
        assert stderr.strip() == 'About to exit with status 0'
