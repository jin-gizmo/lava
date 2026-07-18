"""Assertions for sql/oracle-local/custard-count."""

from __future__ import annotations

import csv
from typing import Any

from lava import LavaError
from lava.connection import get_pysql_connection
from test.conftest import S3path
from test.integration.conftest import HandlerChecker


class Checker(HandlerChecker):
    """Custom checker with isolation for custard-count."""

    def __init__(self, *args, **kwargs) -> None:
        """Init the checker."""
        super().__init__(*args, **kwargs)

        self.conn: Any = None
        self.cursor: Any = None
        self.conn_id = self.job_spec['parameters']['conn_id']
        self.schema = self.fx.tc.db.common.schema
        self.source_table = 'custard'
        self.test_table = self.job_spec['parameters'].get('vars', {}).get(
            'table', 'sql_oracle_custard_count'
        )
        self.table_with_schema = f'{self.schema}.{self.test_table}'

    # --------------------------------------------------------------------------
    def setup(self) -> None:
        """Clone custard data into an isolated table for this test run."""

        self.conn = get_pysql_connection(self.conn_id, self.realm, autocommit=True)
        self.cursor = self.conn.cursor()
        self.cursor.execute(
            f'CREATE TABLE {self.table_with_schema} '
            f'AS SELECT * FROM {self.schema}.{self.source_table}'
        )

    # --------------------------------------------------------------------------
    def teardown(self) -> None:
        """Drop the isolated custard table."""

        if self.conn:
            cursor = self.conn.cursor()
            cursor.execute(f'DROP TABLE IF EXISTS {self.table_with_schema}')
            self.conn.close()

    # --------------------------------------------------------------------------
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

        output = job_result.get('output', {})
        assert len(output) == 1

        output_files = next(iter(output.values()))
        assert len(output_files) == 1

        data = S3path(output_files[0]).read().decode('utf-8').splitlines()
        rows = list(csv.reader(data, delimiter='|'))
        assert len(rows) == 1
        assert rows[0][0].strip() == '100'
