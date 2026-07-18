"""Assertions for the hello-world.yaml cmd job."""

from __future__ import annotations

import json
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
        """Check function for lava-jobs/cmd/plain job."""

        assert job_result is not None
        assert job_result['exit_status'] == 0
        assert job_error is None

        # We should see the job spec emitted as JSON in one of the log records from
        # the run. Let's find it.
        for m in self.fx.caplog.get_records('call'):
            try:
                logged_job_spec = json.loads(m.message)
            except json.JSONDecodeError:
                continue
            break
        else:
            assert False, 'Could not find logged job spec in log events'

        # Compare a few fields
        for k in ('job_id', 'run_id', 'description', 'type', 'realm'):
            assert (
                logged_job_spec[k] == self.job_spec[k]
            ), f'Mismatch on {k}: {logged_job_spec[k]} != {self.job_spec[k]}'
