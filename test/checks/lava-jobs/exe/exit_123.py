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
        """Check function for lava-jobs/exe/exit-123 job."""

        assert job_result is None
        assert isinstance(job_error, LavaError)
        assert str(job_error) == 'Failed with exit status 123'

        assert (
            job_events[(self.job_id, self.run_id)][-1]['info']['error_data']['exit_status'] ==
            123
        )
