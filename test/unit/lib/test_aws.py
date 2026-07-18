"""Test AWS lib functions."""

import moto.core
import pytest  # noqa

from lava.lib.aws import *
from test.conftest import use_moto


# ------------------------------------------------------------------------------
@use_moto
def test_ssm_get_param(aws_mock_creds):
    # Need to import within the scope of the mock
    import lava.lib.aws

    name = '/lava-test/string'
    value = 'abcd efgh'
    ssm = boto3.client('ssm')
    moto.core.patch_client(ssm)
    ssm.put_parameter(
        Name=name,
        Description='For lava unit tests',
        Value='abcd efgh',
        Type='String',
    )

    assert lava.lib.aws.ssm_get_param(name) == value


# ------------------------------------------------------------------------------
class TestAwsS3Utils:
    @pytest.mark.parametrize(
        's,result',
        [
            ('s3://mybucket.com.au/a/prefix', ('mybucket.com.au', 'a/prefix')),
            ('s3://mybucket.com.au', ('mybucket.com.au', '')),
            ('s3://mybucket.com.au/', ('mybucket.com.au', '')),
            ('s3:mybucket.com.au/a/prefix', ('mybucket.com.au', 'a/prefix')),
            ('mybucket.com.au/a/prefix', ('mybucket.com.au', 'a/prefix')),
            ('mybucket.com.au/a/prefix/', ('mybucket.com.au', 'a/prefix')),
            ('mybucket.com.au', ('mybucket.com.au', '')),
        ],
    )
    def test_aws_s3plit_ok(self, s, result):
        assert s3_split(s) == result

    @pytest.mark.parametrize('s', ['s3://'])
    def test_aws_s3split_bad(self, s):
        with pytest.raises(ValueError, match='Invalid S3 object name'):
            s3_split(s)

    def test_s3_bucket_is_server_logging_enabled(self, secure_bucket):
        assert s3_bucket_is_server_logging_enabled(secure_bucket)

    def test_s3_bucket_is_not_server_logging_enabled(self, unlogged_bucket):
        assert not s3_bucket_is_server_logging_enabled(unlogged_bucket)

    def test_s3_bucket_missing_server_logging_enabled(self, no_such_bucket):
        with pytest.raises(Exception, match='specified bucket does not exist'):
            s3_bucket_is_server_logging_enabled(no_such_bucket)

    def test_s3_bucket_is_encrypted(self, secure_bucket):
        assert s3_bucket_is_encrypted(secure_bucket)

    @use_moto
    def test_s3_bucket_is_public(self):
        name = 'public-test'
        # create_bucket is picky about specifying the region
        s3client = boto3.client('s3', region_name='us-east-1')
        s3client.create_bucket(Bucket=name)
        assert not s3_bucket_is_public(name)

        s3client.put_bucket_acl(Bucket=name, ACL='public-read')
        assert s3_bucket_is_public(name)

    def test_s3_bucket_is_mine(self, secure_bucket):
        assert s3_bucket_is_mine(secure_bucket)

    def test_s3_check_bucket_security(self, secure_bucket):
        assert s3_check_bucket_security(secure_bucket) is None

    @pytest.mark.parametrize(
        'bucket, key, expected',
        [
            ('no-such-bucket', 'some-object', False),
            ('aux', 'no-such-key', False),
            ('aux', 'sentinel', True),
        ],
    )
    def test_s3_object_exists(self, bucket, key, expected):
        assert s3_object_exists(bucket, key) is expected


# ------------------------------------------------------------------------------
class TestDynamo:

    def test_dynamo_unmarshall_item(self, dynamo_json):
        assert dynamo_unmarshall_item(dynamo_json[0]) == dynamo_json[1]

    @pytest.mark.parametrize(
        'value,result',
        [
            ({'S': 'abc'}, 'abc'),
            ({'BOOL': True}, True),
            ({'BOOL': False}, False),
            ({'NULL': True}, None),
            ({'N': '99.9'}, 99.9),
            ({'L': [{'S': 'a'}, {'S': 'b'}]}, ['a', 'b']),
            ({"SS": ["a", "b"]}, {'a', 'b'}),
            ({"B": "YWJjZAo="}, b'abcd\n'),
        ],
    )
    def test_dynamo_unmarshall_value(self, value, result):
        assert dynamo_unmarshall_value(value) == result

    def test_dynamo_scan_table(self):
        realms = list(dynamo_scan_table('lava.realms', boto3.Session()))
        assert realms
