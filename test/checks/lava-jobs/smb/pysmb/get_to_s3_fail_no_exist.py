"""Assertions for smb/pysmb/get-to-s3-fail-no-exist."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import boto3
import jinja2

from lava import LavaError
from test.checks.smb_checker import SMBChecker
from test.conftest import S3path


class Checker(SMBChecker):
    """Custom checker."""

    def __init__(self, *args, **kwargs) -> None:
        """Init checker state."""

        super().__init__(*args, **kwargs)
        self.target_uri = jinja2.Template(self.job_spec['parameters']['file']).render(
            realm=self.realm_info
        )
        self.source_file = Path(self.fx.dirs.smb_share) / 'No such file'

    def setup(self) -> None:
        """Ensure source is absent and output object is clean before running."""

        self.source_file.unlink(missing_ok=True)
        s3path = S3path(self.target_uri)
        boto3.resource('s3').Object(s3path.bucket, s3path.key).delete()

    def teardown(self) -> None:
        """Cleanup source/output state to avoid cross-test contamination."""

        self.source_file.unlink(missing_ok=True)
        s3path = S3path(self.target_uri)
        boto3.resource('s3').Object(s3path.bucket, s3path.key).delete()

    def check(
        self,
        job_result: dict[str, Any] | None,
        job_events: dict[tuple[str, str], list[dict[str, Any]]],
        job_error: LavaError | None,
    ) -> None:
        """Validate smb_get fails for a missing SMB source file."""

        assert job_result is None
        assert job_error is not None
        assert 'Failed with exit status' in str(job_error)
