"""Assertions for an Oracle db_from_s3 drop job."""

from __future__ import annotations

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

        self.conn = None
        self.cursor = None
        self.conn_id = self.job_spec['parameters']['db_conn_id']
        self.schema = self.job_spec['parameters']['schema']
        self.table = self.job_spec['parameters']['table']
        self.test_table = 'tst_' + self.run_id.replace('-', '')[:20]

    def setup(self) -> None:
        """Create a test table by cloning real data table."""

        self.conn = get_pysql_connection(self.conn_id, self.realm, autocommit=True)
        self.cursor = self.conn.cursor()

        self.cursor.execute(
            f'CREATE TABLE {self.schema}.{self.test_table} '
            f'AS SELECT * FROM {self.schema}.{self.table}'
        )

        self.job_spec['parameters']['table'] = self.test_table

    def teardown(self) -> None:
        """Clean up the test table and restore job spec."""

        self.job_spec['parameters']['table'] = self.table
        if self.conn:
            cursor = self.conn.cursor()
            cursor.execute(f'DROP TABLE IF EXISTS {self.schema}.{self.test_table}')
            self.conn.close()

    def check(
        self,
        job_result: dict[str, Any] | None,
        job_events: dict[tuple[str, str], list[dict[str, Any]]],
        job_error: LavaError | None,
    ) -> None:
        """Check function."""

        assert job_result is not None
        assert job_result['exit_status'] == 0
        assert job_error is None

        data_rows = len(
            S3path(f's3://{job_result["bucket"]}/{job_result["key"]}')
            .read()
            .decode('utf-8')
            .splitlines()
        )
        if 'header' in (s.lower() for s in self.job_spec['parameters']['args']):
            data_rows -= 1

        self.cursor.execute(f'SELECT COUNT(*) FROM {self.schema}.{self.test_table}')
        new_row_count = self.cursor.fetchone()[0]

        assert new_row_count == data_rows, 'new_row_count != data_rows'
