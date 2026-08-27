"""Custom checker."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from lava import LavaError
from test.conftest import S3path
from test.integration.conftest import HandlerChecker


# ------------------------------------------------------------------------------
class Checker(HandlerChecker):
    """Custom checker."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.crontab: str | None = None

    def setup(self) -> None:
        """Custom setup."""

        def put_crontab_mock(filename: str) -> None:
            """Put crontab file mock."""
            self.crontab = Path(filename).read_text()

        def get_crontab_mock(filename: str) -> None:
            """Get crontab file mock using data embedded in the job spec."""
            Path(filename).write_text(self.job_spec['x-lava-test']['before'])

        self.fx.monkeypatch.setattr('lava.handlers.lavasched.put_crontab', put_crontab_mock)
        self.fx.monkeypatch.setattr('lava.handlers.lavasched.get_crontab', get_crontab_mock)

    def check(
        self,
        job_result: dict[str, Any] | None,
        job_events: dict[tuple[str, str], list[dict[str, Any]]],
        job_error: LavaError | None,
    ) -> None:
        """Custom checker."""

        assert job_result and job_result['exit_status'] == 0
        assert job_error is None

        old_crontab = S3path(job_result['crontab.old']).read().decode('utf-8')
        assert old_crontab == self.job_spec['x-lava-test']['before']

        new_crontab = S3path(job_result['crontab.new']).read().decode('utf-8')
        assert new_crontab == self.job_spec['x-lava-test']['after']
        assert new_crontab == self.crontab

        event = job_events[self.job_id, self.run_id][-1]
        assert event['status'] == 'complete'
