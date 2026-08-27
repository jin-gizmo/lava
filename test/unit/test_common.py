"""Test AWS lib functions."""

from lava.lib.aws import *
from test.conftest import use_moto


# ------------------------------------------------------------------------------
@use_moto
def test_get_lava_param(aws_mock_creds):
    # Need to import within the scope of the mock
    import lava.common

    name = '/lava-test/string'
    value = 'abcd efgh'
    ssm = boto3.client('ssm')
    ssm.put_parameter(
        Name=name,
        Description='For lava unit tests',
        Value='abcd efgh',
        Type='String',
    )

    assert lava.common.get_lava_param(name, boto3.Session()) == value
