"""Test the logging utils"""

from __future__ import annotations

import builtins
from importlib import reload

import pytest  # noqa

from lava.lib.logging import *

real_import = builtins.__import__


# ------------------------------------------------------------------------------
# noinspection PyShadowingBuiltins
def mock_import(name, globals=None, locals=None, fromlist=(), level=0):
    """Fail when importing colorama."""
    if name == 'colorama':
        raise ImportError('colorama mock')
    return real_import(name, globals, locals, fromlist, level)


# ------------------------------------------------------------------------------
def test_syslog_addreess():
    """
    A perfect example of the complete inanity of unit tests.

    No whales saved.
    """
    assert syslog_address() in {'/dev/log', '/var/run/syslog', ('localhost', 514)}


# ------------------------------------------------------------------------------
@pytest.mark.parametrize(
    'level, expected',
    [
        ('Debug', logging.DEBUG),
        ('info', logging.INFO),
        ('WARNING', logging.WARNING),
    ],
)
def test_get_log_level(level: str, expected: int):
    assert get_log_level(level) == expected


# ------------------------------------------------------------------------------
@pytest.mark.parametrize('level', ['', 'unknown'])
def test_get_log_level_fail(level: str):
    with pytest.raises(ValueError, match='Bad log level'):
        get_log_level(level)


# ------------------------------------------------------------------------------
def test_logging_to_file(tmp_path):
    """Test lava logging to a file."""
    log_file = tmp_path / 'log'
    setup_logging(level='debug', name='lava-test', target=str(log_file))
    logger = logging.getLogger('lava-test')
    for level in ('debug', 'info', 'warning', 'error', 'critical'):
        logger.log(get_log_level(level), f'{level}: Hello world')
    for level in ('debug', 'info', 'warning', 'error', 'critical'):
        assert f'{level}: Hello world' in log_file.read_text()


# ------------------------------------------------------------------------------
@pytest.mark.parametrize('setup_kwargs', [{}, {'colour': False}, {'prefix': 'WOOF'}])
def test_setup_logging_to_stderr(setup_kwargs: dict, capsys):
    """
    Test lava logging to stderr.

    The caplog fixture doesn't work too well here because of the way we fiddle
    with root logger.
    """
    setup_logging(level='debug', name='lava-test', **setup_kwargs)
    logger = logging.getLogger('lava-test')
    for level in ('debug', 'info', 'warning', 'error', 'critical'):
        logger.log(get_log_level(level), f'{level}: Hello world')
        assert f'{level}: Hello world' in capsys.readouterr().err


# ------------------------------------------------------------------------------
@pytest.mark.parametrize(
    'msg,level',
    [
        ('Debug', logging.DEBUG),
        ('Info', logging.INFO),
        ('Warning', logging.WARNING),
        ('Error', logging.ERROR),
        ('Critical', logging.CRITICAL),
    ],
)
def test_setup_logging_to_syslog(msg, level, caplog):
    """
    Test lava logging to syslog facility.

    This is difficult to test because syslog is very platform dependent. At
    least we can check it doesn't crash.
    """
    setup_logging(level='debug', name='lava-test', target='@local0')
    logger = logging.getLogger('lava-test')
    logger.propagate = True
    with caplog.at_level(logging.DEBUG, logger=logger.name):
        logger.log(level, msg)
        assert caplog.record_tuples[-1] == (logger.name, level, msg)


# ------------------------------------------------------------------------------
def test_setup_logging_to_syslog_fail():
    """Test bad syslog facility."""
    with pytest.raises(ValueError, match='Bad syslog facility'):
        setup_logging(level='debug', name='lava-test', target='@nonesuch')


# ------------------------------------------------------------------------------
@pytest.mark.parametrize('tag', [None, 'mytag'])
def test_json_logging(tag: str, tc, tmp_path):
    fields = {
        'localtime': 'asctime',
        'timestamp': 'isotime',  # This is a custom extra in the record
        'level': 'levelname',
        'message': 'message',
        'thread': 'threadName',
        'pid': 'process',
    }
    extra = {
        'event_source': 'lava-test',
        'realm': tc.realm,
    }
    json_formatter = JsonFormatter(fields=fields, extra=extra, tag=tag)

    log_file = tmp_path / 'log'
    setup_logging(level='info', name='lava-test', target=str(log_file), formatter=json_formatter)
    logger = logging.getLogger('lava-test')
    logger.info('Hello world', extra={'a': 'A'})

    log_text = log_file.read_text()
    if tag:
        tag_pfx, log_msg = log_text.split(' ', 1)
        assert tag_pfx == f'{tag}:'
    else:
        log_msg = log_text

    log_rec = json.loads(log_msg)
    assert set(fields) <= set(log_rec)
    assert set(extra) <= set(log_rec)
    assert log_rec['realm'] == tc.realm
    assert log_rec['a'] == 'A'
    assert log_rec['message'] == 'Hello world'


# ------------------------------------------------------------------------------
def test_no_colorama(monkeypatch):
    """Force colorama import to fail."""
    monkeypatch.delitem(sys.modules, 'colorama', raising=False)
    monkeypatch.setattr(builtins, '__import__', mock_import)

    import lava.lib.logging

    reload(lava.lib.logging)

    assert lava.lib.logging.Fore.RESET == '\033[0m'
