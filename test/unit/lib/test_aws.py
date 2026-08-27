"""Test AWS lib functions."""

from base64 import b64encode
from datetime import timedelta
from uuid import uuid4

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
class TestSecManUtils:

    @use_moto
    def test_secman_get_secret_string_ok(self):
        secret_id = str(uuid4())
        secman = boto3.client('secretsmanager')
        data = 'Hello world'

        secman.create_secret(Name=secret_id, SecretString=data)
        assert secman_get_secret(secret_id) == data

    @use_moto
    def test_secman_get_secret_binary_ok(self):
        secret_id = str(uuid4())
        secman = boto3.client('secretsmanager')
        data = b'Hello world'

        secman.create_secret(Name=secret_id, SecretBinary=b64encode(data))
        assert secman_get_secret(secret_id) == data

    @use_moto
    def test_secman_get_secret_binary_not_allowed(self):
        secret_id = str(uuid4())
        secman = boto3.client('secretsmanager')
        data = b'Hello world'

        secman.create_secret(Name=secret_id, SecretBinary=b64encode(data))
        with pytest.raises(Exception, match='Binary secret not allowed'):
            secman_get_secret(secret_id, allow_binary=False)


# ------------------------------------------------------------------------------
@use_moto
def test_sqs_send_msg():
    queue_name = str(uuid4())
    sqs = boto3.client('sqs')
    queue_url = sqs.create_queue(QueueName=queue_name)['QueueUrl']
    data = 'Hello world'

    sqs_send_msg(data, queue_name)

    messages = sqs.receive_message(QueueUrl=queue_url)['Messages']
    assert len(messages) == 1
    assert messages[0]['Body'] == data


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
        assert s3_check_bucket_security(secure_bucket) is None  # noqa

    @use_moto
    def test_s3_set_object_encoding_new_value(self):

        bucket = 'whatever'
        key = str(uuid4())
        aws_session = boto3.Session()
        s3 = aws_session.resource('s3')
        s3.Bucket(bucket).create(
            CreateBucketConfiguration={'LocationConstraint': aws_session.region_name}
        )
        obj = s3.Object(bucket, key)
        obj.put(Body=key.encode('utf-8'), Metadata={'ham': 'spam'})

        # S3 doesn't care what encoding value you set.
        s3_set_object_encoding(bucket, key, 'banana', s3.meta.client)

        # Check ...
        obj.reload()
        assert obj.content_encoding == 'banana'
        assert obj.get()['Body'].read().decode('utf-8') == key
        # Make sure our metadata is preserved
        assert obj.metadata == {'ham': 'spam'}

    @use_moto
    def test_s3_set_object_encoding_same_value(self):

        bucket = 'whatever'
        key = str(uuid4())
        aws_session = boto3.Session()
        s3 = aws_session.resource('s3')
        s3.Bucket(bucket).create(
            CreateBucketConfiguration={'LocationConstraint': aws_session.region_name}
        )
        obj = s3.Object(bucket, key)
        obj.put(Body=key.encode('utf-8'), ContentEncoding='mango', Metadata={'ham': 'spam'})

        # S3 doesn't care what encoding value you set.
        s3_set_object_encoding(bucket, key, 'mango', s3.meta.client)

        # Check ...
        obj.reload()
        assert obj.content_encoding == 'mango'
        assert obj.get()['Body'].read().decode('utf-8') == key
        # Make sure our metadata is preserved
        assert obj.metadata == {'ham': 'spam'}

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

    @use_moto
    def test_s3_load_json_ok(self):

        bucket = 'whatever'
        key = str(uuid4())
        data = {'hello': 'world'}
        aws_session = boto3.Session()
        s3 = aws_session.resource('s3')
        s3.Bucket(bucket).create(
            CreateBucketConfiguration={'LocationConstraint': aws_session.region_name}
        )
        obj = s3.Object(bucket, key)
        obj.put(Body=json.dumps(data).encode('utf-8'))

        result = s3_load_json(bucket, key, aws_session=aws_session)
        assert result == data

    @use_moto
    def test_s3_load_json_no_such_object(self):
        bucket = 'whatever'
        aws_session = boto3.Session()
        s3 = aws_session.resource('s3')
        s3.Bucket(bucket).create(
            CreateBucketConfiguration={'LocationConstraint': aws_session.region_name}
        )

        with pytest.raises(OSError, match='NoSuchKey'):
            s3_load_json(bucket, 'no-such-key', aws_session=aws_session)

    @use_moto
    def test_s3_load_json_bad_data(self):

        bucket = 'whatever'
        key = str(uuid4())
        bad_data = 'this is not JSON'
        aws_session = boto3.Session()
        s3 = aws_session.resource('s3')
        s3.Bucket(bucket).create(
            CreateBucketConfiguration={'LocationConstraint': aws_session.region_name}
        )
        obj = s3.Object(bucket, key)
        obj.put(Body=bad_data.encode('utf-8'))

        with pytest.raises(ValueError, match='Bad JSON'):
            s3_load_json(bucket, key, aws_session=aws_session)


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


# ------------------------------------------------------------------------------
class TestCloudWatchUtils:

    @use_moto
    def test_cw_put_metric_ok(self):

        metric_name = 'weight'
        value = 25
        namespace = 'test'
        dimensions = [
            {'Name': 'Family', 'Value': 'Canidae'},
            {'Name': 'Genus', 'Value': 'Canis'},
            {'Name': 'Species', 'Value': 'Canis lupus'},
        ]
        cwatch = boto3.client('cloudwatch')
        for n in range(5):
            cw_put_metric(
                metric_name,
                namespace,
                [{d['Name']: d['Value']} for d in dimensions],
                value,
                unit=None,
                cw_client=cwatch,
            )

        now = datetime.now(timezone.utc)
        response = cwatch.get_metric_data(
            MetricDataQueries=[
                {
                    'Id': 'xyzzy',
                    'MetricStat': {
                        'Metric': {
                            'Namespace': namespace,
                            'MetricName': metric_name,
                            'Dimensions': dimensions,
                        },
                        'Period': 60,
                        'Stat': 'Maximum',
                    },
                    'ReturnData': True,
                },
            ],
            StartTime=now - timedelta(seconds=60),
            EndTime=now + timedelta(seconds=60),
        )

        assert response['MetricDataResults'][0]['Values'][0] == value
