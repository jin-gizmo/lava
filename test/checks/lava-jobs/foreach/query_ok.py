"""Checker for the query-ok foreach job."""

from __future__ import annotations

import csv
import json
from typing import Any

from lava import LavaError
from test.conftest import get_state_items_by_publisher
from test.integration.conftest import HandlerChecker


# ------------------------------------------------------------------------------
class Checker(HandlerChecker):
    """Custom checker."""

    # --------------------------------------------------------------------------
    def setup(self) -> None:
        """Set up the checker."""

        self.job_spec['globals']['publisher'] = self.run_id

    # --------------------------------------------------------------------------
    def check(
        self,
        job_result: dict[str, Any] | None,
        job_events: dict[tuple[str, str], list[dict[str, Any]]],
        job_error: LavaError | None,
    ) -> None:
        """Check function for lava-jobs/foreach/query-ok job."""

        assert job_result is not None, 'job_result is None'
        assert job_error is None, 'job_error is not None'

        assert job_result['exit_status'] == 0, 'exit status'
        assert job_result['foreach_len'] == 3, 'foreach_len'
        assert job_result['jobs_completed'] == 3, 'jobs_completed'
        assert not job_result['failed_indexes'], 'failed_indexes'

        child_job_id = self.job_spec['payload']
        # job_events should contain results for both the foreach parent job and
        # the child job.
        assert set(job_events) == {
            (self.job_id, self.run_id),
            (child_job_id, self.run_id),
        }, 'job events count'

        # We should have 1 state item created by the child job for each S3 object
        state_items = get_state_items_by_publisher(publisher=self.run_id, realm=self.realm)
        assert len(state_items) == 3, 'state items count'
        foreach_indices = set()

        # Our source table is based on the custard data set -- we cheat here and
        # grab the headers from the source datafile.
        with open(self.fx.td / 'custard100.csv', newline='') as csvfile:
            columns = set(next(csv.reader(csvfile)))

        # Use the state items created by the child to check global propagation.
        for item in state_items:
            child_globals = json.loads(item.value['globals'])
            foreach_indices.add(child_globals['lava']['foreach_index'])
            # Make sure the globals from the parent propagated through to the child job output
            for k, v in self.job_spec['globals'].items():
                if k == 'lava':
                    continue
                assert (
                    child_globals.get(k) == v
                ), f'child global[{k!r}] = {child_globals[k]!r}] != {v!r}'

            # Make sure the field headers from the table make it into globals
            assert columns < set(child_globals), 'columns not in globals'

            # Check some lava specific globals
            for k in ('master_job_id', 'parent_job_id'):
                assert self.job_spec['globals']['lava'][k] == child_globals['lava'][k]
        assert foreach_indices == set(range(3)), 'foreach_index(es)'

        # ------------------------------
        # Check child job events.
        # Should be a starting / running / complete entry for each child run
        child_events = job_events[child_job_id, self.run_id]
        child_completed_events = [d for d in child_events if d['status'] == 'complete']
        assert len(child_completed_events) == 3, 'Child jobs event count'
