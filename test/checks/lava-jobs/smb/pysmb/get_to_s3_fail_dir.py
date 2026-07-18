"""Assertions for smb/pysmb/get-to-s3-fail-dir."""

from __future__ import annotations

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

    def setup(self) -> None:
        """Remove stale output object to avoid false positives."""

        s3path = S3path(self.target_uri)
        boto3.resource('s3').Object(s3path.bucket, s3path.key).delete()

    def teardown(self) -> None:
        """Cleanup output object to keep tests independent."""

        s3path = S3path(self.target_uri)
        boto3.resource('s3').Object(s3path.bucket, s3path.key).delete()

    def check(
        self,
        job_result: dict[str, Any] | None,
        job_events: dict[tuple[str, str], list[dict[str, Any]]],
        job_error: LavaError | None,
    ) -> None:
        """Validate smb_get fails when the source path is a directory."""

        assert job_result is None
        assert job_error is not None
