"""Assertions for sqlc/sqlite3-local/custard-count."""

from __future__ import annotations

import os
import re
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
        """Validate SQL output includes the expected custard row count."""

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

        text = S3path(stdout_path).read().decode('utf-8')
        # The SQLlite query result should be the last integer in the output.
        numbers = re.findall(r'(\d+)', text, flags=re.MULTILINE)
        assert numbers
        assert numbers[-1] == '100'
