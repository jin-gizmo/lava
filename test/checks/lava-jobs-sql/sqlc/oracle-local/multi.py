"""Assertions for sqlc/oracle-local/multi."""

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

        self.conn: Any = None
        self.conn_id = self.job_spec['parameters']['conn_id']
        self.schema = self.fx.tc.db.common.schema
        self.source_table = 'onecol'
        self.test_table = f'tst_{self.run_id}'.replace('-', '_')
        self.table_with_schema = f'{self.schema}.{self.test_table}'
        self.original_table = self.job_spec['parameters'].setdefault('vars', {}).get('table')

    # --------------------------------------------------------------------------
    def setup(self) -> None:
        """Clone onecol data into an isolated table for this test run."""

        self.conn = get_pysql_connection(self.conn_id, self.realm, autocommit=True)
        cursor = self.conn.cursor()
        self.job_spec['parameters'].setdefault('vars', {})['table'] = self.test_table
        cursor.execute(f'DROP TABLE IF EXISTS {self.table_with_schema}')
        cursor.execute(
            f'CREATE TABLE {self.table_with_schema} '
            f'AS SELECT * FROM {self.schema}.{self.source_table}'
        )

    # --------------------------------------------------------------------------
    def teardown(self) -> None:
        """Drop the isolated onecol table and restore vars.table."""

        vars_ = self.job_spec['parameters'].setdefault('vars', {})
        if self.original_table is None:
            vars_.pop('table', None)
        else:
            vars_['table'] = self.original_table

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
        """Validate sqlc output for multi SQL payload."""

        assert job_error is None
        assert job_result is not None
        assert job_result['exit_status'] == 0

        output = job_result.get('output')
        assert isinstance(output, list)
        assert len(output) == 1

        result = output[0]
        assert result['exit_status'] == 0
        assert result['payload'] == 'onecol-multi.sql'
        stdout_path = result.get('stdout')
        assert stdout_path
        assert S3path(stdout_path).read().strip()
