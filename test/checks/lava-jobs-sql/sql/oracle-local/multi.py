"""Assertions for sql/oracle-local/multi."""

from __future__ import annotations

import csv
from typing import Any

from lava import LavaError
from lava.connection import get_pysql_connection
from test.conftest import S3path
from test.integration.conftest import HandlerChecker


class Checker(HandlerChecker):
    """Custom checker."""

    def __init__(self, *args, **kwargs) -> None:
        """Init the checker."""
        super().__init__(*args, **kwargs)

        self.conn: Any = None
        self.cursor: Any = None
        self.conn_id = self.job_spec['parameters']['conn_id']
        self.schema = self.fx.tc.db.common.schema
        self.source_table = 'onecol'
        self.original_table = self.job_spec['parameters']['vars']['table']
        self.test_table = f'tst_{self.run_id}'.replace('-', '_')
        self.table_with_schema = f'{self.schema}.{self.test_table}'

    # --------------------------------------------------------------------------
    def setup(self) -> None:
        """Clone onecol data into an isolated table for this test run."""

        self.conn = get_pysql_connection(self.conn_id, self.realm, autocommit=True)
        self.cursor = self.conn.cursor()
        self.job_spec['parameters']['vars']['table'] = self.test_table
        self.cursor.execute(
            f'CREATE TABLE {self.table_with_schema} '
            f'AS SELECT * FROM {self.schema}.{self.source_table}'
        )

    # --------------------------------------------------------------------------
    def teardown(self) -> None:
        """Drop the isolated onecol table."""

        self.job_spec['parameters']['vars']['table'] = self.original_table

        if self.conn:
            cursor = self.conn.cursor()
            cursor.execute(f'DROP TABLE IF EXISTS {self.table_with_schema}')
            self.conn.close()

    def check(
        self,
        job_result: dict[str, Any] | None,
        job_events: dict[tuple[str, str], list[dict[str, Any]]],
        job_error: LavaError | None,
    ) -> None:
        """Validate multi-query output contains before/after row counts."""

        assert job_error is None
        assert job_result is not None
        assert job_result['exit_status'] == 0

        output = job_result.get('output', {})
        assert len(output) == 1

        output_files = next(iter(output.values()))
        # onecol-multi.sql has two SELECT statements with one INSERT between them.
        assert len(output_files) == 2

        first_rows = list(
            csv.reader(S3path(output_files[0]).read().decode('utf-8').splitlines(), delimiter='|')
        )
        second_rows = list(
            csv.reader(S3path(output_files[1]).read().decode('utf-8').splitlines(), delimiter='|')
        )

        assert len(first_rows) == 1
        assert len(second_rows) == 1

        first = int(first_rows[0][0].strip())
        second = int(second_rows[0][0].strip())
        assert second == first + 1