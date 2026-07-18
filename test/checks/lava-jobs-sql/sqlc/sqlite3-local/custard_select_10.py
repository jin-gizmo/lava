"""Assertions for sqlc/sqlite3-local/custard-select-10."""

from __future__ import annotations

import os
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
        """Validate select output row count for the LIMIT 10 query."""

        assert job_error is None
        assert job_result is not None
        assert job_result['exit_status'] == 0

        output = job_result.get('output')
        assert isinstance(output, list)
        assert len(output) == 1

        result = output[0]
        assert result['exit_status'] == 0
        assert result['payload'] == os.path.basename(self.job_spec['payload'])

        stdout_path = result.get('stdout')
        assert stdout_path

        data = S3path(stdout_path).read().decode('utf-8').splitlines()
        # Ignore non-result lines (e.g. download log chatter) and only keep data rows.
        # The bit about 'Custard' will strip the header line.
        rows = [line for line in data if line.strip() and '|' in line and 'Custard' not in line]
        assert len(rows) == 10
