"""Assertions for sqlc/psql-local/custard-count-iam."""

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
        """Validate sqlc output includes the expected custard row count."""

        assert job_error is None
        assert job_result is not None
        assert job_result['exit_status'] == 0

        output = job_result.get('output')
        assert isinstance(output, list)
        assert len(output) == 1

        result = output[0]
        assert result['exit_status'] == 0
        assert result['payload'] == 'custard-count.sql'

        stdout_path = result.get('stdout')
        assert stdout_path
        data = S3path(stdout_path).read().decode('utf-8').splitlines()
        rows = list(csv.reader(data, delimiter='|'))
        values = [row[0].strip() for row in rows if row and row[0].strip().isdigit()]

        assert values
        assert values[-1] == '100'
