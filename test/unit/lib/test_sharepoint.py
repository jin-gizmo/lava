"""Test the sharepoint module."""

import pytest

from lava.lib.sharepoint import *

D1 = {'a': 'A', 'b': {'c': 'C'}}
D2 = {'x': 'X', 'y': {'z': 'Z'}}


# ------------------------------------------------------------------------------
@pytest.mark.parametrize(
    'key,val,obj,expected',
    [
        ('a', 'A', D1, True),
        ('a', 'X', D1, False),
        ('a', ['X', 'a'], D1, False),
        ('b.c', 'C', D1, True),
        ('a', 'A', 'this-is-not-an-object', False),
        ('a', KeyExists(), D1, True),
        ('b.c', KeyExists(), D1, True),
        ('b.c', None, D1, False),
        ('b.c', None, {'a': 'A', 'b': {'c': None}}, True),
    ],
)
def test_key_val_match(key, val, obj, expected):
    assert key_val_match(key, val, obj) is expected


# ------------------------------------------------------------------------------
@pytest.mark.parametrize(
    'data, match, expected',
    [
        ([D1, D2], [('a', 'A')], D1),
        ([D1, D2], [('y.z', 'Z')], D2),
        ([D1, D2], [('y.z', 'nope')], None),
    ],
)
def test_first_matching(data, match, expected):
    assert first_matching(data, match) is expected
