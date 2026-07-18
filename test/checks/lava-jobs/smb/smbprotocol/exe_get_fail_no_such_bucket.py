"""Assertions for split smb exe-get jobs."""

from __future__ import annotations

import re
from typing import Any

from lava import LavaError
from test.conftest import S3path
from test.checks.smb_checker import SMBChecker


class Checker(SMBChecker):
    """Custom checker."""

    def __init__(self, *args, **kwargs) -> None:
        """Init checker state."""

        super().__init__(*args, **kwargs)
        self.init_split_triplet()
        self.configure_split_get_source()

    def check(
        self,
        job_result: dict[str, Any] | None,
        job_events: dict[tuple[str, str], list[dict[str, Any]]],
        job_error: LavaError | None,
    ) -> None:
        """Validate the scripted SMB get test reports expected status."""

        assert job_result is None
        assert job_error is not None
        output = (job_error.data or {}).get('output', [])

        assert len(output) == 1

        stdout_uri = output[0].get('stdout')
        assert stdout_uri

        stdout = S3path(stdout_uri).read().decode('utf-8')
        statuses = [int(match.group(1)) for match in re.finditer(r'Status was (\d+):', stdout)]
        assert len(statuses) == 1
        assert statuses[0] == self.expected_status
