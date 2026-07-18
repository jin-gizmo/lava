"""Assertions for sqli/sqlite3-local/custard-select-dialect-unix."""

from __future__ import annotations

import csv
from typing import Any

from lava import LavaError
from test.conftest import S3path
from test.integration.conftest import HandlerChecker


class Checker(HandlerChecker):
    """Custom checker."""

    def check(
        self,
        job_result: dict[str, Any] | None,
        job_events: dict[tuple[str, str], list[dict[str, Any]]],
        job_error: LavaError | None,
    ) -> None:
        """Validate select output row count and unix dialect-like quoting."""

        assert job_error is None
        assert job_result is not None
        assert job_result['exit_status'] == 0

        output = job_result.get('output', {})
        assert isinstance(output, dict)
        assert len(output) == 1

        output_files = output.get('0')
        assert output_files is not None
        assert len(output_files) == 1

        text = S3path(output_files[0]).read().decode('utf-8')
        rows = list(csv.reader(text.splitlines(), delimiter=','))

        assert len(rows) == 10
        assert all(len(row) > 0 for row in rows)
        assert '"' in text
