"""Test generic connector."""

import subprocess
from copy import deepcopy

import pytest

import lava.connection
from lava.connection.generic import (
    _ATTRIBUTE_TYPE_HANDLERS,  # noqa
    _generic_connection,  # noqa
    cli_connect_generic,
)
from lava import LavaError

GENERIC_CONN_CONTENT = {
    'a': 'String a',
    'b': 'This is multi-line string b with 3 lines.\nLine 2.\nLine 3.\n',
    'c': 30,  # int
    'd': 20.4,  # float
    'e': 'String for e',  # Local param with compound format
    'f': 'This generic parameter came from SSM.',  # Secure param from SSM
    'g': True,  # Bool param
    'h': None,  # None param
}

# import lava.connection.generic

GENERIC_CONN_NAME = 'generic'


# ------------------------------------------------------------------------------
@pytest.fixture(scope='session')
def generic_conn_spec(tc):
    """Retrieve the generic connector conn spec."""
    conn_id = f'{tc.prefix.conn}/{GENERIC_CONN_NAME}'
    return lava.connection.get_connection_spec(conn_id, realm=tc.realm)


# ------------------------------------------------------------------------------
@pytest.fixture(scope='function')
def generic_conn_spec_copy(generic_conn_spec):
    """Create a mutable copy of the generic conn spec."""
    return deepcopy(generic_conn_spec)


# ------------------------------------------------------------------------------
def test_get_generic_connection(tc):

    conn_id = f'{tc.prefix.conn}/{GENERIC_CONN_NAME}'
    conn = lava.connection.get_generic_connection(conn_id, realm=tc.realm)
    assert conn == GENERIC_CONN_CONTENT


# ------------------------------------------------------------------------------
@pytest.mark.parametrize(
    'attr_spec, exc, match',
    [
        ({'type': 'local'}, Exception, 'value must be specified for attributes of type "local"'),
        ({'type': 'ssm'}, Exception, 'parameter must be specified for attributes of type "ssm"'),
    ],
)
def test_param_type_fail(attr_spec: dict, exc: type(Exception), match: str):
    attr_handler = _ATTRIBUTE_TYPE_HANDLERS[attr_spec['type']]
    with pytest.raises(exc, match=match):
        attr_handler(attr_spec)


# ------------------------------------------------------------------------------
def test_cli_connect_generic(generic_conn_spec, tmp_path):
    conn_cli = cli_connect_generic(generic_conn_spec, workdir=str(tmp_path))
    for k, v in GENERIC_CONN_CONTENT.items():
        proc = subprocess.run([conn_cli, k], capture_output=True, check=True, text=True)
        assert proc.stdout == str(v)


# ------------------------------------------------------------------------------
def test__generic_connection_bad_field(generic_conn_spec):
    mutated_conn_spec = dict(**generic_conn_spec, bad_field='whatever')
    with pytest.raises(LavaError, match='Unexpected keys: bad_field'):
        _generic_connection(mutated_conn_spec)


# ------------------------------------------------------------------------------
def test__generic_connection_bas_attr_spec(generic_conn_spec_copy):
    generic_conn_spec_copy['attributes'] = 'should-be-dict'
    with pytest.raises(LavaError, match='attributes field must be a dict'):
        _generic_connection(generic_conn_spec_copy)


# ------------------------------------------------------------------------------
def test__generic_connection_bad_attr_name(generic_conn_spec_copy):
    generic_conn_spec_copy['attributes']['a/bad/nane'] = 'something'
    with pytest.raises(LavaError, match='Bad attribute name: a/bad/nane'):
        _generic_connection(generic_conn_spec_copy)


# ------------------------------------------------------------------------------
def test__generic_connection_bad_attr_type(generic_conn_spec_copy):
    generic_conn_spec_copy['attributes']['x'] = {'type': 'unknown'}
    with pytest.raises(LavaError, match='Unknown attribute type: unknown'):
        _generic_connection(generic_conn_spec_copy)


# ------------------------------------------------------------------------------
def test__generic_connection_bad_attr_object(generic_conn_spec_copy):
    generic_conn_spec_copy['attributes']['x'] = ['cannot-be-a-list']
    with pytest.raises(LavaError, match='Unsupported attribute type'):
        _generic_connection(generic_conn_spec_copy)


# ------------------------------------------------------------------------------
def test__generic_connection_bad_attr_ssm(generic_conn_spec_copy):
    generic_conn_spec_copy['attributes']['x'] = {'type': 'ssm', 'parameter': 'no-such-ssm-param'}
    with pytest.raises(LavaError, match='ParameterNotFound'):
        _generic_connection(generic_conn_spec_copy)
