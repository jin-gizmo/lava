"""Test lava config()."""

import os

import pytest  # noqa

from test.const import REALM
from lava.config import config, config_load
from lava.lib.datetime import duration_to_seconds
from lava.lib.misc import size_to_bytes, str2bool


# ------------------------------------------------------------------------------
@pytest.mark.parametrize(
    'key,convert, expected',
    [
        ('TMPDIR', None, '/tmp/lava'),
        ('CW_METRICS_PERIOD', duration_to_seconds, 60),
        ('DEBUG', str2bool, False),
        ('A_FAKE_SIZE', size_to_bytes, 100 * 1000),
        ('A_FAKE_BOOL', str2bool, True),
    ],
)
def test_config_ok(key, convert, expected):
    os.environ['LAVA_A_FAKE_SIZE'] = '100K'
    os.environ['LAVA_A_FAKE_BOOL'] = 'yes'
    assert config(key, convert) == expected


def test_config_bad():
    os.environ['LAVA_A_BAD_BOOL'] = 'wotcha'
    with pytest.raises(Exception, match='Cannot convert config item'):
        config('A_BAD_BOOL', size_to_bytes)


# ------------------------------------------------------------------------------
# TODO need to mock out the realms table properly
def test_config_load():
    cfg = config_load(REALM)
    # noinspection PyTestUnpassedFixture
    assert isinstance(cfg, dict) and cfg == config_load.realm_info
    # config_load is idempotent
    assert config_load(REALM) == cfg
