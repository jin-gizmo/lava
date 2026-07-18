"""Test the daemon module."""

import pytest

from lava.lib.daemon import *


# ------------------------------------------------------------------------------
def test_lock_file(tmp_path):
    lock = tmp_path / "lock"

    assert lock_file(str(lock))
    assert lock.is_file()
    assert int(lock.read_text()) == os.getpid()


# ------------------------------------------------------------------------------
@pytest.mark.parametrize(
    'sig',
    [
        signal.SIGUSR1,
        'sigusr1',
        'USR1',
    ],
)
def test_set_signal(sig):
    # noinspection PyUnusedLocal
    def handler(sig_num: int, frame):
        """Basic signal"""
        print('SIGNAL', sig_num)

    orig_handler = signal.getsignal(signum(sig))
    try:
        set_signal(sig, handler)
        assert signal.getsignal(signum(sig)) is handler

        # Ignore the signal
        set_signal(sig)
        assert signal.getsignal(signum(sig)) is signal.SIG_IGN
    finally:
        # Restore
        set_signal(sig, orig_handler)


def test_set_signal_fail():
    with pytest.raises(ValueError):
        set_signal(signal.SIGUSR1, 'must-be-callable')


# ------------------------------------------------------------------------------
def test_stop_core_dumps():
    assert resource.getrlimit(resource.RLIMIT_CORE) != (0, 0)
    stop_core_dumps()
    assert resource.getrlimit(resource.RLIMIT_CORE) == (0, 0)
