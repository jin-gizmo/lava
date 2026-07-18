"""Test OS lib functions."""

import pytest  # noqa

from lava.lib.os import *


# ------------------------------------------------------------------------------
@pytest.mark.parametrize(
    'sig,expected',
    [
        ('int', 2),
        ('sigint', 2),
        ('SIGINT', 2),
        (2, 2),
    ],
)
def test_signum_ok(sig, expected):
    assert signum(sig) == expected


@pytest.mark.parametrize(
    'sig',
    [
        999,
        'frog',
    ],
)
def test_signum_bad(sig):
    with pytest.raises(ValueError):
        signum(sig)


# ------------------------------------------------------------------------------
@pytest.mark.parametrize(
    'sig,expected',
    [
        (2, 'SIGINT'),
        ('int', 'SIGINT'),
    ],
)
def test_signame_ok(sig, expected):
    assert signame(sig) == expected


@pytest.mark.parametrize(
    'sig',
    [
        999,
    ],
)
def test_signame_bad(sig):
    with pytest.raises(ValueError):
        signame(sig)


# ------------------------------------------------------------------------------
def test_makedirs(tmpdir):
    makedirs(os.path.join(tmpdir, 'test'))
    with pytest.raises(OSError, match='File exists'):
        makedirs(os.path.join(tmpdir, 'test'))
    makedirs(os.path.join(tmpdir, 'test'), mode=0o0700, exist_ok=True)
