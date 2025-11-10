"""
Generic connector.

The generic connector is essentially inert. It provides a grouping mechanism
for related parameters and also handles the decryption of any encrypted
SSM parameter values.

The conn spec looks like this:

```json
{
    "conn_id": "whatever",
    "description": "Sample generic connector",
    "enabled": true,
    "type": "generic",
    "attributes": {
        "a": "...",
        "b": {
            "type": "local",
            "value": "whatever"
        },
        "c": {
            "type": "ssm",
            "parameter": "/lava/realm/my-var"
        }
    }
}
```

"""

from __future__ import annotations

import os
import re
from decimal import Decimal
from stat import S_IRUSR, S_IWUSR, S_IXUSR
from tempfile import mkdtemp
from typing import Any

import boto3

from lava.common import get_lava_param
from lava.lib.misc import decimal_to_scalar, dict_check
from .core import (
    CONNECTION_OPTIONAL_FIELDS,
    CONNECTION_REQUIRED_FIELDS,
    IGNORE_FIELDS,
    LOG,
    LavaError,
    cli_connector,
    get_connection_spec,
)

__author__ = 'Murray Andrews'

GENERIC_CONNECTION_REQUIRED_FIELDS = CONNECTION_REQUIRED_FIELDS | {'attributes'}
GENERIC_CONNECTION_OPTIONAL_FIELDS = CONNECTION_OPTIONAL_FIELDS

ATTRIBUTE_NAME_RE = r'^[a-zA-Z][\w-]*$'

_ATTRIBUTE_TYPE_HANDLERS = {}

# The CLI script assumes the value for each attribute is in a file with same name.
CLI_SCRIPT = """#!/bin/bash
VALUE_DIR="{value_dir}"
if [ $# -ne 1 ]
then
    echo Usage: $(basename $0) param_name >&2
    exit 1
fi
if [ ! -f "$VALUE_DIR/$1" ]
then
    echo "$1: No such parameter" >&2
    exit 1
fi
cat "$VALUE_DIR/$1"
"""


# ..............................................................................
# region attribute handlers
# ..............................................................................


# ------------------------------------------------------------------------------
def attribute_type(*args: str):
    """
    Register a paramter type handler for generic connector attributes.

    Usage:

    ```python
    @attribute_type('attribute_type', ...)
    a_func(conn_spec)
    ```

    :param args:        A list of parameter types that the decorated function
                        handles.
    """

    def decorate(func):
        """
        Register the handler function.

        :param func:    Function to register.
        :return:        Unmodified function.

        """
        for p_type in args:
            if p_type in _ATTRIBUTE_TYPE_HANDLERS:
                raise Exception(f'{p_type} is already registered')
            _ATTRIBUTE_TYPE_HANDLERS[p_type] = func
        return func

    return decorate


# ------------------------------------------------------------------------------
# noinspection PyUnusedLocal
@attribute_type('local')
def param_type_local(param_spec: dict[str, Any], aws_session: boto3.Session = None) -> str:
    """
    Extract a local value.

    :param param_spec:      The parameter spec dictionary. Must contain a
                            `value` key
    :param aws_session:     A boto3 session.

    :return:                The parameter value.
    """

    try:
        return param_spec['value']
    except KeyError:
        raise Exception('value must be specified for attributes of type "local"')


# ------------------------------------------------------------------------------
@attribute_type('ssm')
def param_type_ssm(param_spec: dict[str, Any], aws_session: boto3.Session = None) -> str:
    """
    Extract an SSM value.

    :param param_spec:      The parameter spec dictionary. Must contain a
                            `parameter` key
    :param aws_session:     A boto3 session.

    :return:                The parameter value.
    """

    try:
        return get_lava_param(param_spec['parameter'], aws_session=aws_session)
    except KeyError:
        raise Exception('parameter must be specified for attributes of type "ssm"')


# ..............................................................................
# endregion attribute handlers
# ..............................................................................


# ------------------------------------------------------------------------------
def _generic_connection(
    conn_spec: dict[str, Any], aws_session: boto3.Session = None
) -> dict[str, Any]:
    """
    Get a Python generic connection.

    This is basically just a dict of attribute values for the connector. What
    happens then is entirely up to the caller.

    :param conn_spec:       Connection specification
    :param aws_session:     A boto3 Session(). This is used to get credentials.

    :return:                Name of an executable that implements the connection.

    """
    pass

    try:
        dict_check(
            conn_spec,
            required=GENERIC_CONNECTION_REQUIRED_FIELDS,
            optional=GENERIC_CONNECTION_OPTIONAL_FIELDS,
            ignore=IGNORE_FIELDS,
        )
    except Exception as e:
        raise LavaError(f'Connection {conn_spec.get("conn_id")}: {e}')

    conn_id = conn_spec['conn_id']
    attribute_specs = conn_spec['attributes']
    if not isinstance(attribute_specs, dict):
        raise LavaError(f'Connection {conn_id}: attributes field must be a dict')

    # ----------------------------------------
    # Get attribute values. Note that Dynamo can return numbers as Decimal

    attr_values = {}
    for attr_name, attr_spec in attribute_specs.items():
        if not re.match(ATTRIBUTE_NAME_RE, attr_name):
            raise LavaError(f'Connection {conn_id}: Bad attribute name: {attr_name}')
        # Scalars are handled directly
        if isinstance(attr_spec, Decimal):
            attr_spec = decimal_to_scalar(attr_spec)
        if attr_spec is None or isinstance(attr_spec, (int, float, str, bool)):
            attr_values[attr_name] = attr_spec
            continue

        if not isinstance(attr_spec, dict):
            raise LavaError(
                f'Connection: {conn_id}: Unsupported attribute type {type(attr_spec)}'
                f' for attribute {attr_name}'
            )

        attr_spec.setdefault('type', 'local')

        # Get a handler for other attribute types
        try:
            attr_handler = _ATTRIBUTE_TYPE_HANDLERS[attr_spec['type']]
        except KeyError:
            raise LavaError(f'Connection: {conn_id}: Unknown attribute type: {attr_spec["type"]}')

        try:
            attr_values[attr_name] = attr_handler(attr_spec, aws_session=aws_session)
        except Exception as e:
            raise LavaError(f'Connection {conn_id}: {e}')

    return attr_values


# ------------------------------------------------------------------------------
def get_generic_connection(
    conn_id: str, realm: str, aws_session: boto3.Session = None
) -> dict[str, Any]:
    """
    Get a generic connection.

    Connection params area:

    - `attributes`:
        Essentially a map of key:value pairs. See the
        [generic connector][connector-type-generic] for more
        information.

    :param conn_id:         Connection ID.
    :param realm:           Realm.
    :param aws_session:     A boto3 Session().

    :return:                A dictionary of resolved attributes.
    """

    conn_spec = get_connection_spec(conn_id, realm, aws_session=aws_session)
    return _generic_connection(conn_spec, aws_session=aws_session)


# ------------------------------------------------------------------------------
@cli_connector('generic')
def cli_connect_generic(
    conn_spec: dict[str, Any], workdir: str, aws_session: boto3.Session = None
) -> str:
    """
    Generate a CLI command to deliver values from a generic connector.

    The CLI command accepts a single positional argument that is the name of the
    element in the generic connection. See
    [Using the Generic Connector][using-the-generic-connector]
    for more information.

    :param conn_spec:       Connection specification
    :param workdir:         Working directory name.
    :param aws_session:     A boto3 Session(). This is used to get credentials.

    :return:                Name of an executable that implements the connection.

    """

    attr_values = _generic_connection(conn_spec, aws_session=aws_session)

    # ----------------------------------------
    # Create the files containing the values

    conn_dir = mkdtemp(dir=workdir, prefix='conn.')
    value_dir = os.path.join(conn_dir, 'values')
    os.mkdir(value_dir, mode=0o700)

    for name, value in attr_values.items():
        with open(os.path.join(value_dir, name), 'w') as fp:
            fp.write(str(value))

    # ----------------------------------------
    # Create the shell script to yield values

    conn_script = CLI_SCRIPT.format(value_dir=value_dir)
    LOG.debug(f'Conn script is {conn_script}')

    conn_cmd_file = os.path.join(conn_dir, 'get-attr-value')
    with open(conn_cmd_file, 'w') as fp:
        print(conn_script, file=fp)
    os.chmod(conn_cmd_file, S_IRUSR | S_IWUSR | S_IXUSR)

    return conn_cmd_file
