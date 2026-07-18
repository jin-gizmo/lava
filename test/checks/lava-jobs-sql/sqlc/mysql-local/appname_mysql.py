"""Assertions for sqlc/mysql-local/appname-mysql."""

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
        """Validate appname query output has header and at least one row."""

        assert job_error is None
        assert job_result is not None
        assert job_result['exit_status'] == 0

        output = job_result.get('output')
        assert isinstance(output, list)
        assert len(output) == 1

        result = output[0]
        assert result['exit_status'] == 0
        assert result['payload'] == 'mysql-program-name.sql'
        stdout_path = result.get('stdout')
        assert stdout_path

        text = S3path(stdout_path).read().decode('utf-8')
        dialect = csv.Sniffer().sniff(text, delimiters='|,;\t')
        rows = list(csv.reader(text.splitlines(), dialect=dialect))

        assert len(rows) >= 2
        header = [col.strip().strip('"').lower() for col in rows[0]]
        assert 'program_name' in header
        assert all(len(row) > 0 for row in rows[1:])
