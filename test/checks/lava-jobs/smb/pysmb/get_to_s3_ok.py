"""Assertions for smb/pysmb/get-to-s3-ok."""

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
            realm=self.realm_info,
            job={'run_id': self.run_id},
        )
        self.conn_id = self.job_spec['parameters']['conn_id']
        self.share_name = self.job_spec['parameters']['share_name']
        filename = self.target_uri.rsplit('/', 1)[-1]
        share_file = self.fx.dirs.smb_share / self.run_id / filename
        remote_file = share_file.relative_to(self.fx.dirs.smb_share).as_posix()
        self.share_content = f'hello-world,{self.run_id}\n'

        self.configure_smb_source(
            conn_id=self.conn_id,
            share_name=self.share_name,
            remote_source=remote_file,
            share_file=share_file,
            share_content=self.share_content,
            seed_source=True,
        )

    def setup(self) -> None:
        """Prepare SMB source data and remove stale S3 output object."""

        super().setup()

        s3path = S3path(self.target_uri)
        boto3.resource('s3').Object(s3path.bucket, s3path.key).delete()

    def teardown(self) -> None:
        """Cleanup output object and SMB source file to keep tests independent."""

        s3path = S3path(self.target_uri)
        boto3.resource('s3').Object(s3path.bucket, s3path.key).delete()
        super().teardown()

    def check(
        self,
        job_result: dict[str, Any] | None,
        job_events: dict[tuple[str, str], list[dict[str, Any]]],
        job_error: LavaError | None,
    ) -> None:
        """Validate smb_get copied a non-empty file to S3."""

        assert job_error is None
        assert job_result is not None
        assert job_result['exit_status'] == 0

        assert job_result['destination'] == self.target_uri
        data = S3path(self.target_uri).read().decode('utf-8')
        assert data == self.share_content
