"""
End-to-end tests for the cmd handler driven by job JSON fixtures.

Test cases are loaded from test/jobs/lava-jobs/cmd/ — only files with
type equal to cmd are selected.  Each JSON fixture is transformed into
a full job spec via conftest.make_job_spec and executed through
lava.lava.run_job.

The x-lava-expected-result field in each fixture encodes the expected
outcome:

-  OK   → the handler should succeed (exit_status == 0)
-  FAIL → the handler should raise LavaError

Fixtures missing x-lava-expected-result are skipped.  A matching handler
module loaded via conftest._load_handler performs the final assertion.
"""

from __future__ import annotations

import logging
import re
from types import SimpleNamespace
from typing import Any

import boto3
import pytest  # noqa

from conftest import HandlerChecker, load_custom_checks
from lava import LavaError
from lava.lava import run_job
from lava.lavacore import augment_job_spec, get_job_spec, make_dispatch_msg
from test.conftest import DotDict
from test.const import WORKER

__author__ = 'James Nguyen'

# ------------------------------------------------------------------------------
# Tests
# ------------------------------------------------------------------------------


class TestHandler:
    """Run each cmd job JSON fixture through the handler and assert on the outcome."""

    def test_jobs(
        self,
        x_lava_test: dict[str, Any],
        realm_info: DotDict,
        tc: DotDict,
        tmp_path,
        fx,
        monkeypatch,
        capfd,
        caplog,
    ):
        """
        Execute a fixture-defined job and validate its outcome with a check function.

        This test mirrors worker-side behavior by creating a dispatch message,
        reloading the persisted job spec from DynamoDB so optional fields are
        initialized, augmenting the spec as it would be on SQS pickup, and then
        running the job via run_job. If execution raises LavaError, the
        exception is captured and forwarded to the check function.

        :param x_lava_test: Test case metadata loaded from test/conftest.py.
            Expected keys include job_spec, check_path,
            expected_result, and optional error_pattern.
        :param realm_info: Realm metadata and S3 locations required by job execution.
        :param tc: Test context containing realm and related test settings.
        :param tmp_path: Temporary working directory path for the job run.
        :param fx: Fixture accessor passed to dynamic check modules.
        :param monkeypatch: Pytest fixture used to intercept event writes.
        :param capfd: Pytest fixture for stdout/stderr capture.
        :param caplog: Pytest fixture for log capture.
        :return: None.
        :raise AssertionError: If the observed outcome, optional error pattern,
            or check-function assertions do not match expectations.
        """

        # capture logs
        job_events = {}

        caplog.set_level(logging.INFO)

        # ----------------------------------------------------------------------
        def put_event(mesg):
            """Capture event records that would normally go to the DynamoDB events table."""
            job_id = mesg.get('job_id')
            run_id = mesg.get('run_id')

            job_events.setdefault((job_id, run_id), []).append(mesg)

        # ----------------------------------------------------------------------
        monkeypatch.setattr('lava.event.put_event', put_event)

        # AWS related assets
        aws_session = boto3.Session()
        table = aws_session.resource('dynamodb').Table(f'lava.{tc.realm}.jobs')

        # get data from fixture
        job_spec = x_lava_test['job_spec']
        check_path = x_lava_test['check_path']
        expected_result = x_lava_test['expected_result']
        error_pattern = x_lava_test['error_pattern']

        # we create this so that we can run augment_job_spec later
        # this also add the 'ts_dispatch' field to the job spec which is required by the check
        dispatch_msg = make_dispatch_msg(
            realm=tc.realm,
            job_id=job_spec['job_id'],
            worker=WORKER,
            params=job_spec.get('params'),
            aws_session=aws_session,
            globals_=job_spec.get('globals'),
        )

        # fetch from DynamoDB so we can have the optional fields initialized properly
        job_spec = get_job_spec(job_id=job_spec['job_id'], jobs_table=table)
        job_spec = augment_job_spec(job_dispatch=dispatch_msg, job_spec=job_spec, realm=tc.realm)

        job_run_result = None
        job_run_error = None
        context = SimpleNamespace()  # Placeholder for future use.

        checker_cls = check.Checker if (check := load_custom_checks(check_path)) else HandlerChecker
        with checker_cls(
            job_spec=job_spec, realm_info=realm_info, fx=fx, context=context
        ) as checker:
            try:
                job_run_result = run_job(
                    job_spec,
                    {
                        'realm': realm_info.realm,
                        's3_payloads': realm_info.s3_payloads,
                        's3_temp': realm_info.s3_temp,
                        's3_key': realm_info.s3_key,
                    },
                    str(tmp_path),
                    dev_mode=False,
                    aws_session=aws_session,
                )
                outcome = 'OK'
            except LavaError as exc:
                job_run_error = exc
                outcome = 'FAIL'

            assert (
                outcome == expected_result
            ), f'{job_spec.get("job_id")}: expected {expected_result} but got {outcome}'

            if error_pattern and job_run_error:
                assert re.search(error_pattern, str(job_run_error))

            # We're enforcing keyword args here because there will be lots of these
            # little checkers and we want to minimise risk of accidents.
            checker.check(job_result=job_run_result, job_events=job_events, job_error=job_run_error)
