"""Custom checker."""

from __future__ import annotations

import json
from typing import Any

from lava import LavaError
from test.conftest import S3path
from test.integration.conftest import HandlerChecker


# ------------------------------------------------------------------------------
class Checker(HandlerChecker):
    """Custom checker."""

    def check(
        self,
        job_result: dict[str, Any] | None,
        job_events: dict[tuple[str, str], list[dict[str, Any]]],
        job_error: LavaError | None,
    ) -> None:
        """Check function for lava-jobs/pkg/db-conn job."""

        assert job_result and job_result['exit_status'] == 0
        assert not job_error

        assert job_events[self.job_id, self.run_id][-1]['info']['exit_status'] == 0

        output_filename = job_result['output'][0]['stdout']
        result = json.loads(S3path(output_filename).read().decode('utf-8'))

        # The result should have one python and one CLI output for each connection
        # in the job
        assert len(result) == 2 * len(self.job_spec['parameters']['connections'])

        for k, v in result.items():
            if k.startswith('LAVA_CONNID_'):
                assert v['result'] == [1], f'Py connector error for {k}'
            elif k.startswith('LAVA_CONN_'):
                # Just check we got something
                assert v['stdout'], f'CLI error for {k}'
