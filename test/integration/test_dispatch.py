"""
End-to-end dispatch tests for the cmd handler.

Jobs are dispatched to SQS and results verified via the events table.
A lava worker must be running to pick up dispatched jobs::

    ./lava-worker --realm test --worker core

Test cases are loaded from the same YAML fixtures used by
test_e2e_cmd.TestCmdHandlerEndToEnd.
"""

from __future__ import annotations

from test.const import WORKER

import boto3
import pytest  # noqa
from conftest import get_result_from_event, poll_event

from lava.lavacore import dispatch

__author__ = 'James Nguyen'


# ------------------------------------------------------------------------------
# Tests
# ------------------------------------------------------------------------------


class TestJobDispatch:
    """
    Dispatch cmd jobs to SQS and verify results via the events table.

    A lava worker must be running to pick up dispatched jobs::

        ./lava-worker --realm test --worker core
    """

    @pytest.mark.skip(
        'Requires a running lava worker, does not support coverage report, out of scope'
    )
    def test_job(self, _x_lava_test, tc):
        """
        Dispatch a fixture-defined cmd job and validate the final event status.

        The test sends the job to SQS, waits for the worker completion event in
        DynamoDB, and compares the observed status with x-lava-test-result from
        the fixture. Expected OK requires complete status and exit_status of 0.
        Any other expected value requires failed status.

        :param _x_lava_test: The test fixture containing the necessary information.
        :param tc: Test context with the target realm.
        :return: None.
        :raise AssertionError: If dispatch fails or the observed result does not
            match expectation.
        """
        aws_session = boto3.Session()
        events_table = aws_session.resource('dynamodb').Table(f'lava.{tc.realm}.events')

        job_spec = _x_lava_test['job_spec']
        check_path = _x_lava_test['check_path']

        job_id = job_spec['job_id']
        expected_result = job_spec.get('x-lava-test-result', '').upper()
        expect_ok = expected_result == 'OK'

        # Dispatch the job — the worker fetches the spec from DynamoDB.
        run_id = dispatch(
            realm=tc.realm,
            job_id=job_id,
            aws_session=aws_session,
            worker=WORKER,
        )
        assert run_id, 'dispatch should return a run_id'

        # Poll the events table until the worker finishes the job.

        event = poll_event(events_table, job_id, run_id)
        status = event['status']
        result = get_result_from_event(event)

        if expect_ok:
            assert (
                status == 'complete'
            ), f'{check_path.stem}: expected complete but got status={status}, info={result}'
            exit_status = result.get('exit_status', -1)
            assert (
                int(exit_status) == 0
            ), f'{check_path.stem}: expected exit_status=0 but got {exit_status}'
        else:
            assert (
                status == 'failed'
            ), f'{check_path.stem}: expected failed but got status={status}, info={result}'
