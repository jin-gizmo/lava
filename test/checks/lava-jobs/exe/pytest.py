"""Assertions for the pytest.yaml exe job."""

from __future__ import annotations

from typing import Any

from lava import LavaError
from lava import __version__
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
        """Check function for lava-jobs/exe/pytest job."""

        assert job_result is not None
        assert job_result['exit_status'] == 0
        assert job_error is None

        # Check the content of our job output
        output_file = S3path(job_result['output'][0]['stdout'])
        stdout = output_file.read().decode('utf-8')
        assert __version__ in stdout
