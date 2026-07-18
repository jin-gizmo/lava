"""
Shared fixtures for tests using ministack as AWS mock infrastructure.

Ministack (ministack.org) is a local AWS emulator. Tests expect it to be
running and the AWS_ENDPOINT_URL environment variable to be set
(e.g. http://localhost:4566).

The ministack realm is bootstrapped by test/config/ministack-setup.sh
which hardcodes the following values:

-   REALM  = test
-   WORKER = core
-   S3 buckets: cfn, lava, code, log
-   SQS worker queue: lava-test-core
-   CloudFormation stack lava-test creates the DynamoDB tables
    (lava.realms, lava.test.jobs, lava.test.events, etc.)

See also test/config/realm-cfn-cli.yaml for the CFN parameters that
define the realm (lavaBucketName=lava, logBucketName=log, etc.).
"""

from __future__ import annotations

import importlib.util
import time
from pathlib import Path
from types import ModuleType, SimpleNamespace
from typing import Any

import pytest  # noqa
from lava import LavaError
from test.conftest import DotDict, FixtureAccessor

__author__ = 'James Nguyen'

CHECKS_DIR = Path(__file__).parent.parent / 'checks'


# ------------------------------------------------------------------------------
# Setup
# ------------------------------------------------------------------------------
def pytest_runtest_setup(item):
    """
    Skip or validate a test item based on job spec metadata.

    Reads result and marks from the
    parametrised x_lava_test_job_spec fixture value. Tests missing the initial
    mark or a valid expected-result field are skipped automatically.

    :param item: The pytest test item being set up.
    :raise ValueError: If x-lava-test-result is present but not OK or FAIL.
    """
    if hasattr(item, 'callspec'):
        params = item.callspec.params

        fixture = params['x_lava_test']
        job_spec = fixture.get('job_spec')

        if not job_spec:
            pytest.skip('Missing job spec in x-lava-test fixture')

        test_metadata = job_spec.get('x-lava-test', {})
        # handle expected test result
        expected_result = test_metadata.get('result', '').upper()

        if not expected_result:
            pytest.skip('Missing result in x-lava-test')

        if expected_result not in ['OK', 'FAIL']:
            raise ValueError(f'Unexpected expected result: {expected_result}')


# ------------------------------------------------------------------------------
# Poll helpers
# ------------------------------------------------------------------------------
POLL_INTERVAL = 2  # seconds between polls
POLL_TIMEOUT = 60  # max seconds to wait for a terminal status
TERMINAL_STATUSES = {'complete', 'failed'}


def poll_event(events_table, job_id: str, run_id: str, timeout: int = POLL_TIMEOUT) -> dict:
    """
    Poll the DynamoDB events table until the job reaches a terminal status.

    Checks every POLL_INTERVAL seconds and returns as soon as the item's
    status field is in TERMINAL_STATUSES.

    :param events_table: The boto3 DynamoDB Table resource to query.
    :param job_id: The job identifier to look up.
    :param run_id: The run identifier to look up.
    :param timeout: Maximum seconds to wait; defaults to POLL_TIMEOUT.
    :return: The full event item from DynamoDB once a terminal status is reached.
    :raise TimeoutError: If the job does not reach a terminal status within *timeout* seconds.
    """
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        resp = events_table.get_item(Key={'job_id': job_id, 'run_id': run_id})
        item = resp.get('Item')
        if item and item.get('status') in TERMINAL_STATUSES:
            return item
        time.sleep(POLL_INTERVAL)

    raise TimeoutError(f'Job {job_id} ({run_id}) did not reach a terminal status within {timeout}s')


def get_result_from_event(event: dict) -> dict:
    """
    Extract the result info dict from the last terminal log entry of an event.

    Walks the log list in reverse to find the most recent entry whose
    status is in TERMINAL_STATUSES, and returns its info sub-dict.

    :param event: A DynamoDB event item containing a log list.
    :return: The info dict from the last terminal log entry, or {} if none is found.
    """
    log = event.get('log', [])
    for entry in reversed(log):
        if entry.get('status') in TERMINAL_STATUSES:
            return entry.get('info', {})
    return {}


# ------------------------------------------------------------------------------
# Dynamic handler & job loading
# ------------------------------------------------------------------------------
def load_custom_checks(check_path: Path) -> ModuleType | None:
    """
    Load the assertion handler module that corresponds to *filename*.

    Searches HANDLERS_DIR recursively for a .py file whose stem
    matches the normalised form of *filename*.  Returns None when no
    handler is found.  Raises when multiple candidate files are found so
    that ambiguous setups are never silently ignored.

    :param check_path: A Path pointing to the check function.
    :return: The loaded handler module, or None if no handler file exists.
    :raise RuntimeError: If more than one handler file matches the module name.
    """

    if not check_path.is_file():
        return None

    spec = importlib.util.spec_from_file_location(f'custom_checks.{check_path.stem}', check_path)

    if spec is None or spec.loader is None:
        return None

    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


# ------------------------------------------------------------------------------
class HandlerChecker:
    """
    Custom handler checker for lava job handlers.

    This is a context manager.

    The base class is not abstract because we want a no-op checker as our fallback.

    :param job_spec:    Augmented lava job specification.
    :param realm_info:  Lava realm info.
    :param fx:          Accessor for pytest fixtures (e.g. fx.tmp_path)
    :param context:     Reserved for future use.

    """

    # --------------------------------------------------------------------------
    def __init__(
        self,
        job_spec: dict[str, Any],
        realm_info: DotDict,
        fx: FixtureAccessor,
        context: SimpleNamespace,
    ):
        """Create a custom handler checker for lava job handlers."""
        self.job_spec = job_spec
        self.realm_info = realm_info
        self.fx = fx
        self.context = context
        # Convenience vars
        self.job_id = job_spec['job_id']
        self.run_id = job_spec['run_id']
        self.realm = realm_info.realm

    # --------------------------------------------------------------------------
    # noinspection PyMethodMayBeStatic
    def setup(self) -> None:
        """Perform any setup actions required for this checker."""
        pass

    # --------------------------------------------------------------------------
    # noinspection PyMethodMayBeStatic
    def teardown(self) -> None:
        """Perform any teardown actions required for this checker."""
        pass

    # --------------------------------------------------------------------------
    def check(
        self,
        job_result: dict[str, Any] | None,
        job_events: dict[tuple[str, str], list[dict[str, Any]]],
        job_error: LavaError | None,
    ) -> None:
        """
        Perform any checks required for this checker.

        This method is not abstract because it is possible that a test job needs
        some setup / teardown but does not need a custom checker. So the default
        checker is a no-op.

        :param job_result:  Result dict from executing the lava job. Typically None
                            if the job failed.
        :param job_events:  A list of log events from the job execution that would
                            normally go to the DynamoDB events table.
        :param job_error:   Exception thrown by a failed lava job.
        """

        pass

    # --------------------------------------------------------------------------
    def __enter__(self):
        """Enter the context manager."""
        self.setup()
        return self

    # --------------------------------------------------------------------------
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Exit the context manager."""
        self.teardown()
        return False
