"""Isolation setup for sqlv/mssql-local/custard-rollback."""

from __future__ import annotations

from typing import Any

from lava.connection import get_pysql_connection
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
        self.source_table = 'custard'
        self.original_table = self.job_spec['parameters']['vars']['table']
        self.test_table = f'tst_{self.run_id}'.replace('-', '_')
        self.table_with_schema = f'{self.schema}.{self.test_table}'

    # --------------------------------------------------------------------------
    def setup(self) -> None:
        """Clone custard data into an isolated table for this test run."""

        self.conn = get_pysql_connection(self.conn_id, self.realm, autocommit=True)
        self.cursor = self.conn.cursor()
        self.job_spec['parameters']['vars']['table'] = self.test_table
        self.cursor.execute(f'DROP TABLE IF EXISTS {self.table_with_schema}')
        self.cursor.execute(
            f'SELECT * INTO {self.table_with_schema} '
            f'FROM {self.schema}.{self.source_table}'
        )

    # --------------------------------------------------------------------------
    def teardown(self) -> None:
        """Drop the isolated custard table."""

        self.job_spec['parameters']['vars']['table'] = self.original_table

        if self.conn:
            cursor = self.conn.cursor()
            cursor.execute(f'DROP TABLE IF EXISTS {self.table_with_schema}')
            self.conn.close()
