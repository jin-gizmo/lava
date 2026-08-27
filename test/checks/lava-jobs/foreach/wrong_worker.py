"""Checker for the inline/ok foreach job."""

from __future__ import annotations

from test.integration.conftest import HandlerChecker


# ------------------------------------------------------------------------------
class Checker(HandlerChecker):
    """Custom checker."""

    def setup(self) -> None:
        """Setup the checker."""

        self.job_spec['worker'] = 'not-same-as-child'
