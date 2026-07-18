"""Assertions for sql/oracle-local/select-single."""

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
        """Validate select-single output parses correctly even when table is empty."""

        assert job_error is None
        assert job_result is not None
        assert job_result['exit_status'] == 0

        output = job_result.get('output', {})
        assert len(output) == 1

        output_files = next(iter(output.values()))
        assert len(output_files) == 1

        data = S3path(output_files[0]).read().decode('utf-8').splitlines()
        rows = list(csv.reader(data, delimiter='|'))

        if rows:
            assert all(len(row) > 0 for row in rows)