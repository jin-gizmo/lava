"""Test the state manager utilities."""

import re
from dataclasses import dataclass
from datetime import datetime
from itertools import product
from typing import Any

import pytest

from lava import LavaError
from lava.lib.state import LavaStateItem, state_types


# ------------------------------------------------------------------------------
@dataclass
class StateItemValue:
    """Container for a state item."""

    v_type: str
    value: Any


TEST_VALUES = (
    StateItemValue('simple', 'hello world'),
    StateItemValue('complex', {'a': 'hello world', 'b': 24, 'c': [1, 2, 3]}),
)

STATE_TYPES = ('raw', 'secure', 'json')


# ------------------------------------------------------------------------------
@pytest.fixture(scope='module')
def session_id() -> str:
    """Create a uniqye ID to localise state vars to a test run."""
    return datetime.now().strftime('%Y%m%d-%H%M%S')


# ------------------------------------------------------------------------------
def test_state_types():
    assert set(STATE_TYPES) == set(state_types())


# ------------------------------------------------------------------------------
@pytest.mark.parametrize('state_type, value', product(STATE_TYPES, TEST_VALUES))
def test_state_item(state_type: str, value: StateItemValue, session_id, tc):
    state_id = f'lava/test/{session_id}/{state_type}/{value.v_type}'
    LavaStateItem.new(
        state_type,
        realm=tc.realm,
        state_id=state_id,
        value=value.value,
        publisher='lava-test',
        ttl='1h',
    ).put()

    state_item = LavaStateItem.get(state_id, tc.realm)
    assert state_item.value == value.value
    assert re.search(f"state_id='{state_id}'", str(state_item))


# ------------------------------------------------------------------------------
def test_state_item_bad_type(tc):
    with pytest.raises(LavaError, match='No such state type'):
        LavaStateItem.new(
            'unknown-type',
            realm=tc.realm,
            state_id='does not matter',
            value='hello world',
            publisher='lava-test',
            ttl='1h',
        )
