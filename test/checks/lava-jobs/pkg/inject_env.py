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
        """Check function for lava-jobs/pkg/inject-env job."""

        assert job_result and job_result['exit_status'] == 0
        assert not job_error

        assert job_events[self.job_id, self.run_id][-1]['info']['exit_status'] == 0

        stdout_filename = job_events[self.job_id, self.run_id][-1]['info']['output'][0]['stdout']
        stdout = S3path(stdout_filename).read().decode('utf-8')
        # Check some lava and non-lava env vars propagated o
        for k, v in [
            ('X_RUN_ID', self.run_id),
            ('LAVA_JOB_ID', self.job_id),
            ('LAVA_RUN_ID', self.run_id),
            ('LAVA_REALM', self.realm),
        ]:
            assert f'{k}={v}\n' in stdout, f' Expected {k}={v}\n'
