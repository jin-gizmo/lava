"""Pytest conf."""

from __future__ import annotations

import http.client
import json
import os
import re
from collections.abc import Iterator
from functools import wraps
from pathlib import Path
from typing import Any
from urllib.parse import urlencode, urlparse

import boto3
import pytest  # noqa
import yaml
from boto3.dynamodb.types import TypeDeserializer
from lava.lavacore import get_realm_info
from lava.lib.aws import s3_split
from lava.lib.state import LavaStateItem
from moto import mock_aws as _mock_aws
from smart_open import open
from test.cli_helpers import (
    patch_mysql_cli_to_docker,
    patch_psql_cli_to_docker,
    patch_sqlplus_cli_to_docker,
)
from test.const import REALM, TARGET_MARKS

TEST_CONFIG = 'conftest.yaml'

LAVA_BASE = Path(__file__).parent.parent
TEST_BASE = Path(__file__).parent

# This is also available as fixture `td` -- see below
DIRS = {
    'cwd': Path('.').resolve(),
    'src': LAVA_BASE,
    'etc': LAVA_BASE / 'etc',
    'schema': LAVA_BASE / 'lava' / 'lib' / 'schema',
    'services': TEST_BASE / 'services',
    'data': TEST_BASE / 'data',
    'smb_share': TEST_BASE / 'services' / 'smb' / 'share.x',
    'jobs': TEST_BASE / 'jobs' / 'dist' / REALM,  # Test jobs base dir
    'checks': TEST_BASE / 'checks',
}


# ------------------------------------------------------------------------------
def read_s3_manifest_data(s3object: str) -> list[list[str]]:
    """Read the data files listed in a manifest file."""

    manifest_data = json.loads(S3path(s3object).read())
    result = []

    # We use smart_open because the files could be gzzipped
    for item in manifest_data['entries']:
        with open(item['url']) as f:
            result.append(f.read().splitlines())
    return result


# ------------------------------------------------------------------------------
def get_state_items_by_publisher(
    publisher: str, realm: str, aws_session: boto3.Session | None = None
) -> list[LavaStateItem]:
    """Get all state items for a given publisher."""

    if not aws_session:
        aws_session = boto3.Session()

    dynamodb = aws_session.client('dynamodb')
    deserializer = TypeDeserializer()
    paginator = dynamodb.get_paginator('scan')
    state_items = []
    for page in paginator.paginate(
        TableName=f'lava.{realm}.state',
        FilterExpression='publisher = :pub',
        ProjectionExpression='state_id',
        ExpressionAttributeValues={':pub': {'S': publisher}},
    ):
        for item in page.get('Items', []):
            state_id = deserializer.deserialize(item['state_id'])
            state_items.append(LavaStateItem.get(state_id, realm, aws_session=aws_session))

    return state_items


# ------------------------------------------------------------------------------
@pytest.fixture(scope='session', autouse=True)
def add_bin_path():
    """
    Ensure that the repo bin/ directory is in the PATH for all tests.

    This is required for tests that invoke CLI utilities (e.g. lava-smb)
    that are built from the repo source code.
    """
    repo_bin = str(LAVA_BASE / 'bin')
    path = os.environ.get('PATH', '')
    if repo_bin not in path.split(':'):
        os.environ['PATH'] = f'{repo_bin}:{path}' if path else repo_bin


# ------------------------------------------------------------------------------
@pytest.fixture(scope='function', autouse=True)
def sqlc_mysql_docker_cli(request, monkeypatch):
    """
    Route sqlc MySQL jobs through the dockerized mysql CLI image.

    This fixture scaffolds integration tests that execute sqlc jobs without a
    host mysql client installed. It only applies to parametrized handler tests
    where the job type is sqlc and the conn_id targets a MySQL-family
    connection.
    """

    if 'x_lava_test' not in request.fixturenames:
        return

    x_lava_test = request.getfixturevalue('x_lava_test')
    job_spec = x_lava_test.get('job_spec', {})

    if job_spec.get('type') != 'sqlc':
        return

    params = job_spec.get('parameters', {})
    conn_id = str(params.get('conn_id', '')).lower()
    if '/db/mysql/' not in conn_id and '/db/mariadb/' not in conn_id:
        return

    from test.const import DOCKER_NETWORK

    image = os.environ.get('LAVA_TEST_MYSQL_CLI_IMAGE', 'mysql-cli-oracle')
    network = os.environ.get('LAVA_TEST_DOCKER_NETWORK', DOCKER_NETWORK)
    tmp_path = request.getfixturevalue('tmp_path')
    patch_mysql_cli_to_docker(monkeypatch, image, tmp_path, network=network)


# ------------------------------------------------------------------------------
@pytest.fixture(scope='function', autouse=True)
def sqlc_sqlplus_docker_cli(request, monkeypatch):
    """
    Route sqlc Oracle jobs through the dockerized sqlplus CLI image.

    This only applies to parametrized handler tests where the job type is sqlc
    and the conn_id targets an Oracle connection.
    """

    if 'x_lava_test' not in request.fixturenames:
        return

    x_lava_test = request.getfixturevalue('x_lava_test')
    job_spec = x_lava_test.get('job_spec', {})

    if job_spec.get('type') != 'sqlc':
        return

    params = job_spec.get('parameters', {})
    conn_id = str(params.get('conn_id', '')).lower()
    if '/db/oracle/' not in conn_id:
        return

    from test.const import DOCKER_NETWORK

    image = os.environ.get('LAVA_TEST_SQLPLUS_CLI_IMAGE', 'sqlplus-cli')
    network = os.environ.get('LAVA_TEST_DOCKER_NETWORK', DOCKER_NETWORK)
    tmp_path = request.getfixturevalue('tmp_path')
    patch_sqlplus_cli_to_docker(monkeypatch, image, tmp_path, network=network)


# ------------------------------------------------------------------------------
@pytest.fixture(scope='function', autouse=True)
def sqlc_psql_docker_cli(request, monkeypatch):
    """
    Route sqlc Postgres jobs through the dockerized psql CLI image.

    This only applies to parametrized handler tests where the job type is sqlc
    and the conn_id targets a Postgres/psql connection.
    """

    if 'x_lava_test' not in request.fixturenames:
        return

    x_lava_test = request.getfixturevalue('x_lava_test')
    job_spec = x_lava_test.get('job_spec', {})

    if job_spec.get('type') != 'sqlc':
        return

    params = job_spec.get('parameters', {})
    conn_id = str(params.get('conn_id', '')).lower()
    if '/db/psql/' not in conn_id and '/db/postgres/' not in conn_id:
        return

    from test.const import DOCKER_NETWORK

    image = os.environ.get('LAVA_TEST_PSQL_CLI_IMAGE', 'psql-cli')
    network = os.environ.get('LAVA_TEST_DOCKER_NETWORK', DOCKER_NETWORK)
    tmp_path = request.getfixturevalue('tmp_path')
    patch_psql_cli_to_docker(monkeypatch, DIRS['etc'], image, tmp_path, network=network)


# ------------------------------------------------------------------------------
def load_test_assets(test_marks: list[str]) -> list[DotDict]:
    """
    Discover and parse all job JSON fixtures under JOBS_DIR.

    Scans JOBS_DIR recursively for *.json files and parses each one.
    The returned path is relative to JOBS_DIR so it can be used directly
    with load_handler.
    :return: A sorted list of (relative_path, job_spec_dict, expected_result) tuples.
    """

    jobs_dir = DIRS['jobs']
    results = []
    for path in sorted(jobs_dir.rglob('*.json')):
        raw = path.read_text()
        job_spec = json.loads(raw)

        test_metadata = job_spec.get('x-lava-test')
        if not test_metadata:
            continue

        expected_result = test_metadata.get('result')
        marks = test_metadata.get('marks', [])
        if set(marks).intersection(test_marks):
            results.append(
                {
                    "job_path": path.relative_to(jobs_dir),
                    "check_path": construct_check_path(path),
                    "job_spec": job_spec,
                    "expected_result": expected_result,
                    "error_pattern": test_metadata.get('error_pattern'),
                }
            )
    return results


# ------------------------------------------------------------------------------
def custom_check_name(filename: str | Path) -> Path:
    """
    Derive a valid Python module name from a job fixture filename.

    Replaces any run of non-word characters in the file stem with _,
    so hello-world.json becomes hello_world.

    :param filename: The fixture filename; only the stem is used.
    :return: A sanitised Python identifier suitable for use as a module name.
    """
    return Path(re.sub(r'\W+', '_', Path(filename).stem))


# ------------------------------------------------------------------------------
def construct_check_path(job_path: Path) -> Path:
    """
    Construct the path to the check module for a given job spec path.

    The check module is expected to be in the same relative location under CHECKS_DIR
    with the same name as the job spec but with a .py extension instead of .json.
    For example, if the job spec is at jobs/dist/test/lava-jobs/cmd/hello-world.yaml,
    the corresponding check module would be at checks/lava-jobs/cmd/hello-world.py.

    :param job_path: The relative path to the job spec JSON file.
    :return: The path to the corresponding check module.
    """

    relative_path = job_path.relative_to(DIRS['jobs'])
    return (
        DIRS['checks'] / relative_path.parent / custom_check_name(job_path.stem).with_suffix('.py')
    )


# ------------------------------------------------------------------------------
def pytest_addoption(parser):
    """Add command line options to pytest."""
    parser.addoption(
        '--test-mark',
        action='append',
        default=None,
        help=(
            'The mark by which to filter lava job specs. Can be used multiple'
            ' times to select job specs with a mark containing any of the'
            ' specified values (i.e. it\'s an OR operator). If not specified,'
            f' jobs marked as the following are selected: {", ".join(TARGET_MARKS)}.'
        ),
    )


# ------------------------------------------------------------------------------
def pytest_generate_tests(metafunc):
    """Parametrize test functions with job specs loaded from *.yaml files."""
    if 'x_lava_test' not in metafunc.fixturenames:
        return

    target_marks = metafunc.config.getoption('--test-mark')
    if not target_marks:
        target_marks = TARGET_MARKS

    jobs = load_test_assets(target_marks)
    job_ids = [job['job_path'].with_suffix('').as_posix() for job in jobs]
    metafunc.parametrize('x_lava_test', jobs, ids=job_ids)


# ------------------------------------------------------------------------------
class DotDict:
    """
    Access dict values with dot notation or conventional dict notation or mix and match.

    ..warning:: This does not handle all dict syntax, just what is needed here.

    """

    def __init__(self, *data: dict[str, Any]):
        """Create dotable dict from dict(s)."""
        self.data = {}

        for d in data:
            self.data.update(d)

    def __getattr__(self, item: str) -> Any:
        """Access config elements with dot notation support for keys."""

        if not item or not isinstance(item, str):
            raise ValueError(f'Bad config item name: {item}')

        try:
            value = self.data[item]
        except KeyError:
            raise AttributeError(item)
        return self.__class__(value) if isinstance(value, dict) else value

    def __getitem__(self, item):
        value = self.data[item]
        return self.__class__(value) if isinstance(value, dict) else value

    def __str__(self):
        return str(self.data)

    def __repr__(self):
        return repr(self.data)


# ------------------------------------------------------------------------------
@pytest.fixture(scope='session')
def td() -> Path:
    """Path for test data."""

    return TEST_BASE / 'data'


# ------------------------------------------------------------------------------
@pytest.fixture(scope='session')
def dirs(td) -> DotDict:
    """Package to access useful directories in the source tree."""

    return DotDict(DIRS)


# ------------------------------------------------------------------------------
@pytest.fixture(scope='session')
def tc() -> DotDict:
    """
    Deliver test configuration data.

    This can be accessed as `tc.a.b.c` or using dictionary notation.

    """

    with open(TEST_BASE / TEST_CONFIG) as fp:
        return DotDict(yaml.safe_load(fp))


# ------------------------------------------------------------------------------
@pytest.fixture(scope='function')
def aws_mock_creds(monkeypatch):
    """Mocked AWS Credentials for moto."""

    monkeypatch.delenv('AWS_PROFILE', raising=False)

    monkeypatch.setenv('AWS_ACCESS_KEY_ID', 'testing')
    monkeypatch.setenv('AWS_SECRET_ACCESS_KEY', 'testing')
    monkeypatch.setenv('AWS_SECURITY_TOKEN', 'testing')
    monkeypatch.setenv('AWS_SESSION_TOKEN', 'testing')
    monkeypatch.setenv('AWS_DEFAULT_REGION', 'us-east-1')


# ------------------------------------------------------------------------------
@pytest.fixture(scope='session', autouse=True)
def set_aws_endpoint_url_env():
    """
    Set the effective AWS endpoint URL.

    We need to make sure our boto calls point at the test AWS environment.  The
    lava CLI "aws" connection is an AWS CLI script with a custom config file
    that will not include an endpoint_url so it will not point at our AWS
    emulator.  So we need to pass that as an env var.
    """

    os.environ['AWS_ENDPOINT_URL'] = boto3.client('sts').meta.endpoint_url


# ------------------------------------------------------------------------------
@pytest.fixture(scope='session')
def aws_account_id() -> str:
    """Get AWS account ID."""

    return boto3.client('sts').get_caller_identity().get('Account')


# ------------------------------------------------------------------------------
@pytest.fixture(scope='session')
def realm_info(tc) -> DotDict:
    """Get the realms table entry for the test realm."""
    realm_table = boto3.Session().resource('dynamodb').Table('lava.realms')
    realm_info = get_realm_info(tc.realm, realm_table)
    return DotDict(realm_info)


# ------------------------------------------------------------------------------
class S3path:
    """Convenience hack for handling S3 paths."""

    def __init__(self, uri: str):
        self.bucket, self.key = s3_split(uri)
        self.uri = f's3://{self.bucket}/{self.key}'

    def __call__(self):
        return self.uri

    def __truediv__(self, other):
        return self.__class__(f'{self.uri}/{other}')

    def __str__(self):
        return self.uri

    def __repr__(self):
        return self.uri

    def read(self) -> bytes:
        """Read the contents of the object specified by the S3 path."""

        return boto3.resource('s3').Object(self.bucket, self.key).get()['Body'].read()


# ------------------------------------------------------------------------------
@pytest.fixture(scope='session')
def s3(realm_info) -> DotDict:
    """Package up useful S3 locations."""

    return DotDict(
        {
            'payloads': S3path(realm_info.s3_payloads),
            'temp': S3path(realm_info.s3_temp),
        }
    )


# ------------------------------------------------------------------------------
def use_moto(func):
    """
    Clean decorator for use with moto.

    This is a clean replacement for moto's @mock_aws that avoids the clash with
    ministack. Moto has this problem that when AWS_ENDPOINT_URL is set, moto
    itself is bypassed so we end up pointing to wherever that points, instead of
    the moto mock.
    """

    @wraps(func)
    def wrapper(*args, **kwargs):
        """Wrap a test function."""
        # The list() here is because otherwise we are modifying while iterating.
        old = {k: os.environ.pop(k) for k in list(os.environ) if k.startswith('AWS_')}
        try:
            with _mock_aws():
                return func(*args, **kwargs)
        finally:
            os.environ |= old

    return wrapper


# ------------------------------------------------------------------------------
class FixtureAccessor:
    """
    Provide simplified, dot-style, access to fixtures.

    This is used where we want clean access to a fixture within a context where
    pytest itself does not provide it through its normal mechanism (e.g. in
    dynamically imported functions).
    """

    def __init__(self, request):
        """Create the fixture accessor."""
        self._request = request

    def __getattr__(self, name):
        """Get a fixture via dot notation."""
        return self._request.getfixturevalue(name)


@pytest.fixture
def fx(request):
    """
    Provide simplified, dot-style, access to fixtures.

    This is used where we want clean access to a fixture within a context where
    pytest itself does not provide it through its normal mechanism (e.g. in
    dynamically imported functions).

    For example, `fx.td` provides a mechanism to access the `td` fixture when
    pytest doesn't make it naturally available.
    """
    return FixtureAccessor(request)


# ------------------------------------------------------------------------------
class SlackEmulateClient:
    """
    Simple client for the vercel slack emulator.

    This is a context manager.
    """

    # --------------------------------------------------------------------------
    def __init__(
        self, token: str, host: str = 'localhost', port: int = 4000, base_url: str | None = None
    ):
        """Initialise the client."""

        if base_url:
            url = urlparse(base_url)
            host, _port = url.netloc.rsplit(':', 1)
            if _port:
                port = int(_port)

        self._token = token
        self._conn = http.client.HTTPConnection(host, port)

    def __enter__(self) -> SlackEmulateClient:
        return self

    def __exit__(self, *exc_info) -> None:
        self.close()

    # --------------------------------------------------------------------------
    def close(self) -> None:
        """Close the connection."""
        self._conn.close()

    # --------------------------------------------------------------------------
    def _post(self, api_method: str, params: dict) -> dict:
        """Wrap posts to include auth."""
        self._conn.request(
            'POST',
            f'/api/{api_method}',
            body=urlencode(params),
            headers={
                'Authorization': f'Bearer {self._token}',
                'Content-Type': 'application/x-www-form-urlencoded',
            },
        )
        resp = self._conn.getresponse()
        data = json.loads(resp.read())
        if not data.get('ok', False):
            raise RuntimeError(f'{api_method} failed: {data.get("error", "unknown_error")}')
        return data

    # --------------------------------------------------------------------------
    def _paginate(self, method: str, params: dict) -> Iterator[dict]:
        """Yield each raw page for a cursor-paginated Slack Web API method."""
        cursor = None
        while True:
            page_params = dict(params, cursor=cursor) if cursor else params
            page = self._post(method, page_params)
            yield page
            cursor = page.get('response_metadata', {}).get('next_cursor')
            if not cursor:
                return

    # --------------------------------------------------------------------------
    def get_conversation_id(self, name: str) -> str | None:
        """Get the ID of a named conversation."""
        for page in self._paginate('conversations.list', {'limit': 200}):
            for channel in page.get('channels', []):
                if channel.get('name') == name:
                    return channel['id']
        return None

    # --------------------------------------------------------------------------
    def get_conversation_messages(self, name: str) -> Iterator[dict]:
        """Yield each message from the named conversation."""
        channel_id = self.get_conversation_id(name)
        if channel_id is None:
            raise ValueError(f'no such conversation: {name!r}')
        for page in self._paginate('conversations.history', {'channel': channel_id, 'limit': 200}):
            yield from page.get('messages', [])

    # --------------------------------------------------------------------------
    @staticmethod
    def match_msg(msg: dict[str, Any], pattern: str) -> bool:
        """
        Check if a message matches the given pattern.

        WARNING: This is an incomplete / hacky version of the (byzantine) Slack
        message structure. It's good enough to check if a message arrived for
        testing purposes.

        """

        pat = re.compile(pattern)
        if pat.search(msg.get('text', '')):
            return True

        for block in msg.get('blocks', []):
            # If this block, of whatever type, has a text field we'll search that.
            txt = block.get('text', {})
            if isinstance(txt, dict):
                s = txt.get('text', '')
            elif isinstance(txt, str):
                s = txt
            else:
                continue

            if pat.search(s):
                return True

        for attachment in msg.get('attachments', []):
            if pat.search(attachment.get('text', '')):
                return True

        return False

    # --------------------------------------------------------------------------
    def search_conversation(self, name: str, pattern: str) -> list[dict]:
        """Find messages in the named conversation matching the specified pattern."""

        return [m for m in self.get_conversation_messages(name) if self.match_msg(m, pattern)]


# --------------------------------------------------------------------------
@pytest.fixture(scope='session')
def slack_emulator_client() -> SlackEmulateClient:
    """Return a simple client for the vercel slack emulator in our local container."""
    return SlackEmulateClient(token='xoxb-fake-token', base_url=os.environ['SLACK_WEBHOOK'])
