"""Test dbnone."""

import pytest  # noqa

from lava.lib.dbnone import dbapi_stub


# ------------------------------------------------------------------------------
def test_connect():
    dummy_module = dbapi_stub('test')
    assert dummy_module.alias == 'test'
    with pytest.raises(NotImplementedError):
        dummy_module.connect()
    with pytest.raises(NotImplementedError):
        dummy_module.Connection()


# ------------------------------------------------------------------------------
def test_cursor():
    dummy_module = dbapi_stub('test_cursor')
    assert dummy_module.alias == 'test_cursor'
    with pytest.raises(NotImplementedError):
        dummy_module.Cursor()
