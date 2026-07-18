"""Assertions for smb/pysmb/put-from-s3-fail-dir."""

from __future__ import annotations

from typing import Any

from lava import LavaError
from test.checks.smb_checker import SMBChecker


class Checker(SMBChecker):
    """Custom checker."""

    def check(
        self,
        job_result: dict[str, Any] | None,
        job_events: dict[tuple[str, str], list[dict[str, Any]]],
        job_error: LavaError | None,
    ) -> None:
        """Validate smb_put fails when destination path points to a directory."""

        assert job_result is None
        assert job_error is not None
        assert 'Failed with exit status' in str(job_error)
