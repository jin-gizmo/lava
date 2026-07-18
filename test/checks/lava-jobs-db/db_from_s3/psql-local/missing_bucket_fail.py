"""Assertions for lava-jobs-db/db_from_s3/psql-local/missing-bucket-fail."""

from __future__ import annotations

from typing import Any

from lava import LavaError
from lava.connection import get_pysql_connection
from test.integration.conftest import HandlerChecker


class Checker(HandlerChecker):
    """Custom checker."""

    def __init__(self, *args, **kwargs) -> None:
        """Init the checker."""
        super().__init__(*args, **kwargs)

        self.conn: Any = None
        self.cursor: Any = None
        self.row_count = 0
        self.conn_id = self.job_spec['parameters']['db_conn_id']
        self.schema = self.job_spec['parameters']['schema']
        self.table = self.job_spec['parameters']['table']
        self.test_table = 'tst_' + self.run_id.replace('-', '_')

    def setup(self) -> None:
        """Clone the target table into an isolated table for this test run."""

        self.conn = get_pysql_connection(self.conn_id, self.realm, autocommit=True)
        self.cursor = self.conn.cursor()
        self.cursor.execute(f'SET SEARCH_PATH TO "{self.schema}"')
        self.cursor.execute(f'CREATE TABLE {self.test_table} AS SELECT * FROM "{self.table}"')
        self.cursor.execute(f'SELECT COUNT(*) FROM {self.test_table}')
        self.row_count = self.cursor.fetchone()[0]
        self.job_spec['parameters']['table'] = self.test_table

    def teardown(self) -> None:
        """Restore the original table name and drop the isolated table."""

        self.job_spec['parameters']['table'] = self.table
        if self.conn:
            cursor = self.conn.cursor()
            cursor.execute(f'DROP TABLE IF EXISTS {self.test_table}')
            self.conn.close()

    def check(
        self,
        job_result: dict[str, Any] | None,
        job_events: dict[tuple[str, str], list[dict[str, Any]]],
        job_error: LavaError | None,
    ) -> None:
        """Validate missing bucket fails and does not mutate table row count."""

        assert job_result is None
        assert job_error is not None
        assert job_events[self.job_id, self.run_id][-1]['status'] == 'failed'

        self.cursor.execute(f'SELECT COUNT(*) FROM {self.test_table}')
        new_row_count = self.cursor.fetchone()[0]
        assert new_row_count == self.row_count
