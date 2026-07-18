"""Assertions for sqli/mysql-local/custard-count-output."""

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
        """Validate SQLI output and custom output area for custard count."""

        assert job_error is None
        assert job_result is not None
        assert job_result['exit_status'] == 0

        output = job_result.get('output', {})
        assert isinstance(output, dict)
        assert len(output) == 1

        output_files = output.get('0')
        assert output_files is not None
        assert len(output_files) == 1
        assert '/my_output_area/' in output_files[0]

        data = S3path(output_files[0]).read().decode('utf-8').splitlines()
        rows = list(csv.reader(data, delimiter='|'))
        assert len(rows) == 1
        assert rows[0][0].strip() == '100'
