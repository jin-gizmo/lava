"""Assertions for sqli/psql-local/custard-rollback."""

from __future__ import annotations

from typing import Any

from lava import LavaError
from lava.connection import get_pysql_connection
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
        self.source_table = 'custard'
        self.test_table = f'tst_{self.run_id}'.replace('-', '_')
        self.table_with_schema = f'{self.schema}.{self.test_table}'
        self.original_payload: list[str] = []
        self.initial_count = 0

    def setup(self) -> None:
        """Clone custard data into an isolated table for this test run."""

        self.conn = get_pysql_connection(self.conn_id, self.realm, autocommit=True)
        self.cursor = self.conn.cursor()
        self.cursor.execute(f'DROP TABLE IF EXISTS {self.table_with_schema}')
        self.cursor.execute(
            f'CREATE TABLE {self.table_with_schema} '
            f'AS SELECT * FROM {self.schema}.{self.source_table}'
        )
        self.cursor.execute(f'SELECT COUNT(*) FROM {self.table_with_schema}')
        self.initial_count = int(self.cursor.fetchone()[0])

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
        """Drop the isolated custard table and restore payload."""

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
        """Validate failed run rolled back table changes in the transaction."""

        assert job_result is None
        assert job_error is not None

        assert self.conn is not None
        cursor = self.conn.cursor()
        cursor.execute(f'SELECT COUNT(*) FROM {self.table_with_schema}')
        count_after = int(cursor.fetchone()[0])
        assert count_after == self.initial_count
