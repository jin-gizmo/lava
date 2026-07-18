"""Test lavacore components."""

from __future__ import annotations

import time as tt  # Need to avoid clash with datetime.time
from unittest import mock

import pytest

from lava.lavacore import *

REALMS_TABLE = boto3.Session().resource('dynamodb').Table('lava.realms')

YESTERDAY = datetime.now().replace(microsecond=0).astimezone() - timedelta(hours=24)
TOMORROW = datetime.now().replace(microsecond=0).astimezone() + timedelta(hours=24)


# ------------------------------------------------------------------------------
def test_scan_realms(tc):
    assert tc.realm in scan_realms()

    attributes = {'realm', 's3_temp'}
    result = scan_realms(attributes=attributes)
    assert attributes == result[tc.realm].keys()


# ------------------------------------------------------------------------------
def test_scan_jobs(tc):

    attributes = {'job_id', 'enabled'}
    jobs = scan_jobs(tc.realm, attributes=attributes)
    for j in jobs.values():
        assert attributes == j.keys()


# ------------------------------------------------------------------------------
def test_get_realm_info(tc):
    result = get_realm_info(tc.realm, REALMS_TABLE)
    assert result['realm'] == tc.realm


# ------------------------------------------------------------------------------
def test_get_realm_info_fail():
    with pytest.raises(Exception, match='No such realm'):
        get_realm_info('no-such-realm', REALMS_TABLE)


# ------------------------------------------------------------------------------
@pytest.mark.parametrize(
    'job_name',
    [
        'cmd/hello-world',
        'exe/pyimport',
    ],
)
def test_get_job_spec(job_name: str, tc):
    job_spec = get_job_spec(
        f'{tc.prefix.job}/{job_name}',
        boto3.Session().resource('dynamodb').Table(f'lava.{tc.realm}.jobs'),
    )

    assert {'job_id', 'type'} <= job_spec.keys()


# ------------------------------------------------------------------------------
@pytest.mark.parametrize(
    'job_name,exc,match',
    [
        ('no-such-job', LavaError, 'No such job'),
        ('bad/no-type', LavaError, 'Bad job record'),
        ('bad/illegal-global', LavaError, 'Reserved global'),
    ],
)
def test_get_job_spec_fail(job_name: str, exc: type[Exception], match: str, tc):
    with pytest.raises(exc, match=match):
        get_job_spec(
            f'{tc.prefix.job}/{job_name}',
            boto3.Session().resource('dynamodb').Table(f'lava.{tc.realm}.jobs'),
        )


# ------------------------------------------------------------------------------
@pytest.mark.parametrize(
    'job_name,warning',
    [
        ('warn/no-description', 'description field will be mandatory in a future release'),
        ('warn/no-owner', 'owner field will be mandatory in a future release'),
        ('warn/unknown-key', 'Job spec deprecation warning: Unexpected keys'),
    ],
)
def test_get_job_spec_warn(job_name: str, warning: str, tc, caplog):
    """Test warning conditions in get_job_spec()."""
    caplog.set_level(logging.WARNING)
    get_job_spec(
        f'{tc.prefix.job}/{job_name}',
        boto3.Session().resource('dynamodb').Table(f'lava.{tc.realm}.jobs'),
    )
    assert warning in caplog.text


# ------------------------------------------------------------------------------
@pytest.mark.parametrize(
    'job_name',
    [
        'cmd/hello-world',
        'exe/pyimport',
    ],
)
def test_jinja_render_vars(job_name, tc):
    """Test jinja_render_vars()."""

    job_spec = get_job_spec(
        f'{tc.prefix.job}/{job_name}',
        boto3.Session().resource('dynamodb').Table(f'lava.{tc.realm}.jobs'),
    )

    # Note that jinja_render_vars is only called once a job is set to run so we
    # have to fake start timestamp.
    job_spec['ts_start'] = datetime.now().astimezone()
    realm_info = {'realm': tc.realm, 'realm_a': 'A', 'realm_b': 'B'}
    render_vars = jinja_render_vars(job_spec, realm_info, test_a='A', test_b='B')

    assert {
        'job',
        'realm',
        'globals',
        'start',
        'state',
        'ustart',
        'utils',
        'test_a',
        'test_b',
    } <= render_vars.keys()


# ------------------------------------------------------------------------------
@pytest.mark.parametrize('job_name', ['exe/email'])
def test_job_environment(job_name, tc):
    """Test job_environment()."""

    job_spec = get_job_spec(
        f'{tc.prefix.job}/{job_name}',
        boto3.Session().resource('dynamodb').Table(f'lava.{tc.realm}.jobs'),
    )
    # Need to fake some vars added at job run-time
    job_spec['realm'] = tc.realm
    job_spec['run_id'] = 'unit-test-run'
    realm_info = {'realm': tc.realm, 's3_payloads': 's3://payloads', 's3_key': 'fake/s3/key'}
    env = job_environment(
        job_spec,
        realm_info,
        base={'test_b': 'will be overridden'},
        render_vars={'realm': realm_info},
        test_a='X',
        test_b='Y',
    )

    expected = {
        'LAVA_OWNER': job_spec['owner'],
        'LAVA_REALM': tc.realm,
        'LAVA_JOB_ID': f'{tc.prefix.job}/{job_name}',
        'LAVA_RUN_ID': 'unit-test-run',
        'LAVA_S3_KEY': 'fake/s3/key',
        'LAVA_WORKER': job_spec['worker'],
        'test_a': 'X',  # extras override other values
        'test_b': 'Y',
    }
    for k, v in expected.items():
        assert env[k] == v


# ------------------------------------------------------------------------------
@pytest.mark.parametrize('job_name', ['exe/email'])
def test_job_environment_fail(job_name, tc):
    """Test job_environment()."""

    job_spec = get_job_spec(
        f'{tc.prefix.job}/{job_name}',
        boto3.Session().resource('dynamodb').Table(f'lava.{tc.realm}.jobs'),
    )
    # Need to fake some vars added at job run-time
    job_spec['realm'] = tc.realm
    job_spec['run_id'] = 'unit-test-run'
    # Add an environment var that is malformed Jinja
    job_spec['parameters'] = {
        'env': {'badvar': '{{ bad jinja syntax'},
    }
    realm_info = {'realm': tc.realm, 's3_payloads': 's3://payloads', 's3_key': 'fake/s3/key'}
    with pytest.raises(LavaError, match='Bad environment variable: badvar:'):
        job_environment(
            job_spec,
            realm_info,
            base={'test_b': 'will be overridden'},
            render_vars={'realm': realm_info},
            test_a='X',
            test_b='Y',
        )


# ------------------------------------------------------------------------------
class TestJobSchedule:
    """Test JobSchedule."""

    @pytest.mark.parametrize('sched', ['* * * * *'])
    def test_simple_cron_sched(self, sched):

        js = JobSchedule(sched)
        assert js.crontab == sched.strip()
        assert js.valid_from == DT_MIN
        assert js.valid_to == DT_MAX
        assert js.active

    @pytest.mark.parametrize(
        'sched,is_active',
        [
            ({'crontab': '* * * * *'}, True),
            ({'crontab': '* * * * *', 'from': YESTERDAY.isoformat()}, True),
            ({'crontab': '* * * * *', 'from': TOMORROW.isoformat()}, False),
            (
                {'crontab': '* * * * *', 'from': TOMORROW.isoformat(), 'to': YESTERDAY.isoformat()},
                False,
            ),
            (
                {'crontab': '* * * * *', 'from': YESTERDAY.isoformat(), 'to': TOMORROW.isoformat()},
                True,
            ),
        ],
    )
    def test_compound_sched(self, sched, is_active):
        js = JobSchedule(sched)
        assert js.active == is_active
        assert re.match(r'[^:]+:', str(js))

    def test_bad_sched_type(self):
        with pytest.raises(LavaError, match='Expected dict'):
            JobSchedule([])  # noqa

    @pytest.mark.parametrize(
        'sched,match',
        [
            ({'no-crontab': '* * * * *'}, 'Missing keys'),
            ({'crontab': '* * * * *', 'bad-key': 'whatever'}, 'Unexpected keys'),
            ({'crontab': '* * * * *', 'from': 'bad-date'}, 'Bad "from"'),
            ({'crontab': '* * * * *', 'to': 'bad-date'}, 'Bad "to"'),
        ],
    )
    def test_bad_dict_sched(self, sched: dict, match: str):
        with pytest.raises(LavaError, match=match):
            JobSchedule(sched)


# ------------------------------------------------------------------------------
THREAD_EXIT = False


def task():
    """A simple task to execute in a thread."""

    end_time = tt.time() + 10
    while not THREAD_EXIT and tt.time() < end_time:
        tt.sleep(0.1)


class TestThreadMonitor:
    """Test the singleton ThreadMonitor class."""

    def test_uniqueness(self):
        tmon = ThreadMonitor()
        assert tmon is ThreadMonitor()

    def test_monitor(self):
        # Bit of a hack to signal our test thread when to finish
        global THREAD_EXIT
        tmon = ThreadMonitor()
        # Register the main thread
        tmon.register_thread()

        # Start a test thread
        t = threading.Thread(target=task, name='test_01')
        tmon.register_thread(t)
        t.start()
        tt.sleep(1)
        assert tmon.thread_status == {'MainThread': 'OK', 'test_01': 'OK'}
        assert tmon.threadcount('test*') == (1, 0)

        THREAD_EXIT = True
        tt.sleep(1)
        assert tmon.thread_status == {'MainThread': 'OK', 'test_01': 'dead'}


# ------------------------------------------------------------------------------
@pytest.mark.parametrize(
    'job_name,params,globals_,delay',
    [
        ('cmd/hello-world', None, None, 0),
        ('cmd/hello-world', {'p1': 'param1'}, None, 0),
        ('cmd/hello-world', {'p1': 'param1'}, {'g1': 'global1'}, 0),
        ('cmd/hello-world', {'p1': 'param1'}, {'g1': 'global1'}, 10),
    ],
)
def test_dispatch(
    job_name: str, params: dict | None, globals_: dict | None, delay: int, tc, monkeypatch
):
    from lava.lib.aws import sqs_send_msg

    mock_sqs_send_message: mock.Mock = mock.create_autospec(sqs_send_msg)
    monkeypatch.setattr('lava.lavacore.sqs_send_msg', mock_sqs_send_message)

    job_id = f'{tc.prefix.job}/{job_name}'
    run_id = dispatch(tc.realm, job_id, params=params, delay=delay, globals_=globals_)

    mock_sqs_send_message.assert_called_once()
    # Grab the dispatch message
    msg = json.loads(mock_sqs_send_message.call_args.args[0])

    assert msg['run_id'] == run_id
    assert msg['job_id'] == job_id
    assert msg['realm'] == tc.realm
    assert msg.get('worker'), 'worker key missing'
    if params:
        assert msg['parameters'] == params
    if globals_:
        assert msg['globals'] == globals_
    assert mock_sqs_send_message.call_args.args[1] == f'lava-{tc.realm}-{msg["worker"]}'
    assert mock_sqs_send_message.call_args.args[2] == delay


# ------------------------------------------------------------------------------
@pytest.mark.parametrize(
    'job_name,params,globals_,exc,match',
    [
        ('cmd/hello-world', 'params-must-be-dict', None, LavaError, 'parameters must be a dict'),
        ('cmd/hello-world', None, 'globals-must-be-dict', LavaError, 'globals must be a dict'),
    ],
)
def test_dispatch_fail(job_name: str, params, globals_, exc: type(Exception), match: str, tc):
    job_id = f'{tc.prefix.job}/{job_name}'
    with pytest.raises(exc, match=match):
        dispatch(tc.realm, job_id, params=params, globals_=globals_)


# ------------------------------------------------------------------------------
@pytest.mark.parametrize(
    'job_name,exc,match',
    [('cmd/hello-world', LavaError, 'swivel')],
)
def test_dispatch_fail_to_send(job_name: str, exc: type(Exception), match: str, tc, monkeypatch):
    from lava.lib.aws import sqs_send_msg

    mock_sqs_send_message: mock.Mock = mock.create_autospec(
        sqs_send_msg, side_effect=Exception('mock send fail')
    )
    monkeypatch.setattr('lava.lavacore.sqs_send_msg', mock_sqs_send_message)

    job_id = f'{tc.prefix.job}/{job_name}'
    with pytest.raises(exc, match=f'Cannot dispatch {job_id}@{tc.realm} - mock send fail'):
        dispatch(tc.realm, job_id)
