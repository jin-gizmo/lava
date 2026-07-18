"""Assertions for a db_from_s3 job."""

from __future__ import annotations

from typing import Any

from lava import LavaError
from lava.connection import get_pysql_connection
from pg8000 import Connection, Cursor
from test.conftest import S3path
from test.integration.conftest import HandlerChecker


# ------------------------------------------------------------------------------
class Checker(HandlerChecker):
    """Custom checker."""

    def __init__(self, *args, **kwargs) -> None:
        """Init the checker."""
        super().__init__(*args, **kwargs)

        self.conn: Connection = None  # noqa
        self.cursor: Cursor = None  # noqa
        self.conn_id = self.job_spec['parameters']['db_conn_id']
        self.schema = self.job_spec['parameters']['schema']
        self.table = self.job_spec['parameters']['table']
        self.test_table = 'tst_' + self.run_id.replace('-', '_')

    # --------------------------------------------------------------------------
    def setup(self) -> None:
        """Create a test table by cloning real data table."""

        self.conn = get_pysql_connection(self.conn_id, self.realm, autocommit=True)
        self.cursor = self.conn.cursor()
        # Not ok in prod code but its ok here in a controlled environment.
        self.cursor.execute(f'SET SEARCH_PATH TO "{self.schema}"')
        self.cursor.execute(f'CREATE TABLE {self.test_table}_a AS SELECT * FROM "{self.table}"')
        self.cursor.execute(f'CREATE TABLE {self.test_table}_b (LIKE "{self.table}")')
        # Patch the job spec to point at test table
        self.job_spec['parameters']['table'] = self.test_table

    # --------------------------------------------------------------------------
    def teardown(self) -> None:
        """Clean up the test table and restore job spec."""
        self.job_spec['parameters']['table'] = self.table
        if self.conn:
            cursor = self.conn.cursor()
            cursor.execute(f'DROP TABLE IF EXISTS {self.test_table}_a')
            cursor.execute(f'DROP TABLE IF EXISTS {self.test_table}_b')
            self.conn.close()

    # --------------------------------------------------------------------------
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

        # How many rows in our source data?
        data_rows = len(
            S3path(f's3://{job_result["bucket"]}/{job_result["key"]}')
            .read()
            .decode('utf-8')
            .splitlines()
        )
        if 'header' in (s.lower() for s in self.job_spec['parameters']['args']):
            data_rows -= 1

        # This is a swtich load so now table _a should be empty and _b loaded
        self.cursor.execute(f'SELECT COUNT(*) FROM {self.test_table}_a')
        row_count_a = self.cursor.fetchone()[0]
        assert row_count_a == 0, 'Expected table A to be empty but it\'s not'

        self.cursor.execute(f'SELECT COUNT(*) FROM {self.test_table}_b')
        row_count_b = self.cursor.fetchone()[0]

        assert row_count_b == data_rows, f'Table b has {row_count_b} rows instead of {data_rows}'
