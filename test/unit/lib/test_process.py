"""Test process utils."""

import os
import subprocess
from logging import getLogger
from threading import Thread
from time import sleep
from uuid import uuid4

import pytest

from lava.lib.misc import Defer
from lava.lib.process import runpg


# ------------------------------------------------------------------------------
def test_runpg_passthru(td, capsys):
    """Test pass through to Python subprocess"""
    proc = runpg(['ls', '-d', td], capture_output=True)
    assert proc.stdout.decode('utf-8').rstrip('\n') == str(td.absolute())


# ------------------------------------------------------------------------------
def test_runpg_basic(td, capsys):
    """Test our implementation with new process group."""
    proc = runpg(['ls', '-d', td.absolute()], start_new_session=True, capture_output=True)
    assert proc.stdout.decode('utf-8').rstrip('\n') == str(td.absolute())


# ------------------------------------------------------------------------------
def test_runpg_bad_args_1(td, capsys):
    """Test our implementation with new process group."""
    with pytest.raises(ValueError, match='may not be used with capture_output'):
        runpg(
            ['ls', '-d', td],
            start_new_session=True,
            capture_output=True,
            stdout=subprocess.PIPE,
        )


# ------------------------------------------------------------------------------
def test_runpg_bad_args_2(td, capsys):
    """Test our implementation with new process group."""
    with pytest.raises(ValueError, match='may not be used with capture_output'):
        runpg(
            ['ls', '-d', td],
            start_new_session=True,
            capture_output=True,
            stdout=subprocess.PIPE,
        )


# ------------------------------------------------------------------------------
def test_runpg_bad_args_3(td, capsys):
    """Test our implementation with new process group."""
    with pytest.raises(ValueError, match='stdin and input arguments may not both be used'):
        runpg(
            ['ls', '-d', td],
            start_new_session=True,
            input=b'abc',
            stdin=subprocess.DEVNULL,
            capture_output=True,
            stdout=subprocess.PIPE,
        )


# ------------------------------------------------------------------------------
def test_runpg_new_session(td, capsys):
    """Test our implementation with new process group."""
    proc = runpg(['cat'], start_new_session=True, input=b'abc\n', capture_output=True)
    assert proc.stdout.decode('utf-8') == 'abc\n'


# ------------------------------------------------------------------------------
def test_runpg_timeout(td, capsys):
    """Test our implementation with new process group."""
    with pytest.raises(subprocess.TimeoutExpired, match='timed out'):
        runpg(['sleep', '30'], start_new_session=True, timeout=1)


# ------------------------------------------------------------------------------
def test_runpg_kill_event_1(td, capsys):
    """Test our implementation with new process group."""
    task_id = str(uuid4())
    runpg(['cat'], start_new_session=True, input=b'abc\n', capture_output=True, kill_event=task_id)
    # The defer task will have been created and cancelled if it all worked.
    assert task_id in Defer.events
    assert len(Defer.events[task_id].tasks) == 0


# ------------------------------------------------------------------------------
def test_runpg_kill_event_2(td, capsys):
    """Test our implementation with new process group."""

    def runcmd(*args, **kwargs):
        """Run a command in a thread."""
        runpg(*args, **kwargs)

    # Run a sleeper in a thread so we can continue and kill it from the side
    task_id = str(uuid4())
    Thread(
        target=runcmd,
        args=(['sleep', '30'],),
        kwargs={'start_new_session': True, 'kill_event': task_id},
    ).start()
    # Give the thread some time to start
    sleep(2)

    # The defer task will have been created and still be there while cmd is active in thread
    assert task_id in Defer.events
    assert len(Defer.events[task_id].tasks) == 1

    deferred: Defer = Defer.events[task_id]
    # The process group kill task will be our only deferred task
    kill_task = next(iter(deferred.tasks.values()))
    pgid = kill_task.args[0]

    # Check process group exists
    os.killpg(pgid, 0)
    # Run our kill task
    deferred.run(logger=getLogger())

    # Give kill a couple of seconds to take effect
    sleep(2)
    with pytest.raises(ProcessLookupError):
        os.killpg(pgid, 0)

    # killpg() is idempotent
    deferred.run(logger=getLogger())
