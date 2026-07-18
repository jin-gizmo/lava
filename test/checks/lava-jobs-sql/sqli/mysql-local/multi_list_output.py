"""Assertions for sqli/mysql-local/multi-list-output."""

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
        """Init checker state."""
        super().__init__(*args, **kwargs)

        self.conn: Any = None
        self.cursor: Any = None
        self.conn_id = self.job_spec['parameters']['conn_id']
        self.schema = self.fx.tc.db.common.schema
        self.source_table = 'onecol'
        self.test_table = f'tst_{self.run_id}'.replace('-', '_')
        self.table_with_schema = f'{self.schema}.{self.test_table}'
        self.original_payload: list[str] = []

    def setup(self) -> None:
        """Clone onecol data into an isolated table for this test run."""

        self.conn = get_pysql_connection(self.conn_id, self.realm, autocommit=True)
        self.cursor = self.conn.cursor()
        self.cursor.execute(
            f'CREATE TABLE IF NOT EXISTS {self.schema}.{self.source_table} (x VARCHAR(50))'
        )
        self.cursor.execute(f'SELECT COUNT(*) FROM {self.schema}.{self.source_table}')
        if int(self.cursor.fetchone()[0]) == 0:
            self.cursor.execute(f"INSERT INTO {self.schema}.{self.source_table} VALUES ('seed')")
        self.cursor.execute(
            f'CREATE TABLE {self.table_with_schema} '
            f'AS SELECT * FROM {self.schema}.{self.source_table}'
        )

        payload = self.job_spec.get('payload', [])
        self.original_payload = list(payload)
        self.job_spec['payload'] = [
            sql.replace(
                f'{self.schema}.{self.source_table}',
                self.table_with_schema,
            )
            for sql in payload
        ]

    def teardown(self) -> None:
        """Drop the isolated onecol table and restore payload."""

        if self.original_payload:
            self.job_spec['payload'] = self.original_payload

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
        """Validate SQLI output contains before/after row counts."""

        assert job_error is None
        assert job_result is not None
        assert job_result['exit_status'] == 0

        output = job_result.get('output', {})
        assert isinstance(output, dict)
        assert len(output) == 3

        first_files = output.get('0')
        middle_files = output.get('1')
        second_files = output.get('2')
        assert first_files is not None
        assert middle_files is not None
        assert second_files is not None

        assert len(first_files) == 1
        assert len(middle_files) == 0
        assert len(second_files) == 1
        assert '/my_output_area/' in first_files[0]
        assert '/my_output_area/' in second_files[0]

        first_rows = list(
            csv.reader(S3path(first_files[0]).read().decode('utf-8').splitlines(), delimiter='|')
        )
        second_rows = list(
            csv.reader(S3path(second_files[0]).read().decode('utf-8').splitlines(), delimiter='|')
        )

        assert len(first_rows) == 1
        assert len(second_rows) == 1

        first = int(first_rows[0][0].strip())
        second = int(second_rows[0][0].strip())
        assert second == first + 1
