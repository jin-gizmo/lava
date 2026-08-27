"""Custom job checker."""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any

from lava import LavaError
from test.integration.conftest import HandlerChecker


# ------------------------------------------------------------------------------
class Checker(HandlerChecker):
    """Custom checker."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.dispatches: list[SimpleNamespace] = []

    def setup(self) -> None:
        """Mock the dispatch() function to capture dispatch events."""

        def dispatch_mock(*args: Any, **kwargs: Any) -> None:
            """Mock the dispatch() function."""
            self.dispatches.append(SimpleNamespace(args=args, kwargs=kwargs))

        self.fx.monkeypatch.setattr('lava.actions.dispatch', dispatch_mock)

    def check(
        self,
        job_result: dict[str, Any] | None,
        job_events: dict[tuple[str, str], list[dict[str, Any]]],
        job_error: LavaError | None,
    ) -> None:
        """Custom checker."""

        ev = job_events[self.job_id, self.run_id][-1]
        assert ev['status'] == 'action_failed'
        assert 'Bad delay' in ev['info']
