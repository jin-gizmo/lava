"""Assertions for sqli/oracle-local/multi-list."""

from __future__ import annotations

from typing import Any

from lava import LavaError
from lava.connection import get_pysql_connection
from test.integration.conftest import HandlerChecker


class Checker(HandlerChecker):
    """Custom checker with isolated onecol table."""

    def __init__(self, *args, **kwargs) -> None:
        """Init checker state."""
        super().__init__(*args, **kwargs)

        self.conn: Any = None
        self.cursor: Any = None
        self.conn_id = self.job_spec['parameters']['conn_id']
        self.schema = self.fx.tc.db.common.schema
        self.base_table = 'onecol'
        self.test_table = 'tso_' + self.run_id.replace('-', '')[:20]
        self.original_payload: list[str] = []

    def setup(self) -> None:
        """Clone onecol into an isolated table and point payload to it."""

        self.conn = get_pysql_connection(self.conn_id, self.realm, autocommit=True)
        self.cursor = self.conn.cursor()

        self.cursor.execute(
            f'CREATE TABLE {self.schema}.{self.test_table} '
            f'AS SELECT * FROM {self.schema}.{self.base_table}'
        )

        payload = self.job_spec.get('payload', [])
        self.original_payload = list(payload)
        self.job_spec['payload'] = [
            sql.replace(
                f'{self.schema}.{self.base_table}',
                f'{self.schema}.{self.test_table}',
            )
            for sql in payload
        ]

    def teardown(self) -> None:
        """Restore payload and drop isolated onecol table."""

        if self.original_payload:
            self.job_spec['payload'] = self.original_payload

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
        """Validate SQLI job succeeded."""

        assert job_error is None
        assert job_result is not None
        assert job_result['exit_status'] == 0
