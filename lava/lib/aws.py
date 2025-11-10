"""AWS utilities."""

from __future__ import annotations

import json
from base64 import b64decode
from collections import OrderedDict
from collections.abc import Iterable, Iterator
from datetime import datetime, timezone
from fnmatch import fnmatch
from functools import lru_cache
from typing import Any

import boto3
import requests
from botocore.exceptions import ClientError

from .decorators import static_vars
from .misc import listify

__author__ = 'Murray Andrews'


# ------------------------------------------------------------------------------
@lru_cache(maxsize=1)
def ec2_instance_id() -> str:
    """
    Get the current machine's EC2 instance ID.

    Assumes IMDSv2.

    :return:            The EC2 instance ID.

    :raise Exception:   If the instance does not appear to be EC2.

    """

    # Get IMDSv2 access token
    r = requests.put(
        'http://169.254.169.254/latest/api/token',
        headers={'X-aws-ec2-metadata-token-ttl-seconds': '21600'},
        timeout=5,
    )
    r.raise_for_status()
    r = requests.get(
        'http://169.254.169.254/latest/meta-data/instance-id',
        headers={'X-aws-ec2-metadata-token': r.text},
        timeout=5,
    )
    r.raise_for_status()
    return r.text


# ------------------------------------------------------------------------------
def ssm_get_param(name: str, decrypt: bool = True, aws_session: boto3.Session = None) -> str:
    """
    Read a secure parameter from AWS SSM service.

    !!! warning
        Does not handle list of string SSM parameters sensibly. This is not a
        problem for lava but be warned before using it more generally.

    :param name:        Valid SSM parameter name
    :param decrypt:     If True, decrypt parameter values. Default True.
    :param aws_session: A boto3 Session. If None a default is created.

    :return:            The parameter value.

    :raise Exception:   If the parameter doesn't exist or cannot be accessed.

    """

    if not aws_session:
        aws_session = boto3.Session()

    ssm = aws_session.client('ssm')
    response = ssm.get_parameter(Name=name, WithDecryption=decrypt)
    return response['Parameter']['Value']


# ------------------------------------------------------------------------------
def secman_get_secret(
    name: str, allow_binary=True, decode_binary=True, aws_session: boto3.Session = None
) -> str | bytes:
    """
    Read a secret from AWS Secrets Manager.

    :param name:        Secret name.
    :param allow_binary: If True allow binary parameters. Default True.
    :param decode_binary: If True, b64 decode binary parameters.
    :param aws_session: A boto3 Session. If None a default is created.
    :return:            The secret value.

    :raise Exception:   If the parameter doesn't exist or cannot be accessed.
    """

    if not aws_session:
        aws_session = boto3.Session()

    sm = aws_session.client('secretsmanager')
    secret = sm.get_secret_value(SecretId=name)

    if 'SecretString' in secret:
        return secret['SecretString']

    if not allow_binary:
        raise Exception('Binary secret not allowed')

    return b64decode(secret['SecretBinary']) if decode_binary else secret['SecretBinary']


# ------------------------------------------------------------------------------
def secman_get_json_secret(name: str, aws_session: boto3.Session = None) -> dict[str, Any]:
    """
    Read a string secret from AWS Secrets Manager containing JSON and decode it.

    :param name:        Secret name.
    :param aws_session: A boto3 Session. If None a default is created.
    :return:            The secret value.

    :raise Exception:   If the parameter doesn't exist or cannot be accessed.
    :return:
    """

    return json.loads(secman_get_secret(name, allow_binary=False, aws_session=aws_session))


# ------------------------------------------------------------------------------
def sqs_send_msg(msg: str, queue_name, delay: int = 0, aws_session: boto3.Session = None) -> None:
    """
    Send a message to an SQS queue.

    :param msg:         The message.
    :param queue_name:  The boto3 queue resource
    :param delay:       Send delay (controlled by SQS).
    :param aws_session: A boto3 Session. If None a default is created.
    """

    if not aws_session:
        aws_session = boto3.Session()

    sqs_queue = aws_session.resource('sqs').get_queue_by_name(QueueName=queue_name)
    sqs_queue.send_message(MessageBody=msg, DelaySeconds=delay)


# ..............................................................................
# region S3 utils
# ..............................................................................


# ------------------------------------------------------------------------------
def s3_split(s: str) -> tuple[str, str]:
    """
    Split an S3 object name into bucket and prefix components.

    :param s:       The object name. Typically `bucket/prefix` but the following
                    are also accepted:

                    ```text
                    s3:bucket/prefix
                    s3://bucket/prefix
                    /bucket/prefix
                    ```

    :return:        A tuple (bucket, prefix)

    """

    # Clean off any s3:// type prefix
    for p in 's3://', 's3:':
        if s.startswith(p):
            s = s[len(p) :]
            break

    t = s.strip('/').split('/', 1)

    if not t[0]:
        raise ValueError(f'Invalid S3 object name: {s}')
    return t[0], t[1].strip('/') if len(t) > 1 else ''


# ------------------------------------------------------------------------------
def s3_download(bucket: str, key: str, filename: str, s3_client) -> None:
    """
    Download object from S3 bucket to a local file.

    :param bucket:      S3 bucket name of source.
    :param key:         Key of source object in source bucket.
    :param filename:    Name of local file in which the object is stored.
    :param s3_client:   boto3 s3 client.

    :raise Exception:   On failure

    """

    try:
        s3_client.download_file(bucket, key, filename)
    except Exception as e:
        raise Exception(f'Download failed: s3://{bucket}/{key} - {e}')


# ------------------------------------------------------------------------------
def s3_upload(bucket: str, key: str, filename: str, s3_client, kms_key: str = None) -> None:
    """
    Upload local file to S3 bucket.

    :param bucket:      S3 bucket name of remote bucket
    :param key:         Key of the object in the remote bucket.

    :param filename:    Name of local file.
    :param s3_client:   boto3 s3 client.
    :param kms_key:     Identifier for a KMS key. If not specified then AES256
                        is used.

    :raise Exception:   On failure

    """

    if kms_key:
        extra_args = {'ServerSideEncryption': 'aws:kms', 'SSEKMSKeyId': kms_key}
    else:
        extra_args = {'ServerSideEncryption': 'AES256'}

    try:
        s3_client.upload_file(filename, bucket, key, ExtraArgs=extra_args)
    except Exception as e:
        raise Exception(f'Upload failed: s3://{bucket}/{key} - {e}')


# ------------------------------------------------------------------------------
def s3_list(
    bucket: str, prefix: str = None, match: str = None, not_match: str = None, s3_client=None
) -> Iterator[str]:
    """
    List an area of an S3 bucket.

    :param bucket:      Bucket name.
    :param prefix:      An optional prefix.
    :param match:       An optional glob style pattern to select files.
    :param not_match:   An optional glob style pattern to skip files.
    :param s3_client:   A boto3 s3 client. One is created if not specified.

    :return:            A generator of object names (without the bucket).
    """

    if not s3_client:
        s3_client = boto3.client('s3')

    args = {'Bucket': bucket}
    if prefix:
        args['Prefix'] = prefix
    paginator = s3_client.get_paginator('list_objects_v2')
    page_iterator = paginator.paginate(**args)
    for page in page_iterator:
        for obj in page.get('Contents', []):
            base = obj['Key'].rsplit('/')[-1]
            if not (match and not fnmatch(base, match)) and not (
                not_match and fnmatch(base, not_match)
            ):
                yield obj['Key']


# ------------------------------------------------------------------------------
def s3_load_json(bucket: str, key: str, aws_session: boto3.Session = None) -> Any:
    """
    Load a JSON file from S3.

    :param bucket:      Name of the S3 bucket.
    :param key:         Object key (file name) for the JSON file
    :param aws_session: A boto3 Session. If None a default is created.

    :return:            The object decoded from the JSON file.

    :raise OSError:     If file doesn't exist or can't be retrieved.
    :raise ValueError:  If the file was retrieved but is not valid JSON.
    """

    if not aws_session:
        aws_session = boto3.Session()

    try:
        response = aws_session.resource('s3').Object(bucket, key).get()
    except Exception as e:
        raise OSError(str(e))

    try:
        return json.load(response['Body'])
    except Exception as e:
        raise ValueError(f'Bad JSON: {e}')


# ------------------------------------------------------------------------------
def s3_check_bucket_security(
    bucket_name: str,
    require_no_public_access: bool = True,
    require_encryption: bool = True,
    require_server_logging: bool = True,
    require_bucket_is_mine: bool = True,
    aws_session: boto3.Session = None,
) -> None:
    """
    Perform a bunch of security checks on am S3 bucket.

    These are described by the various require_* variables.

    :param bucket_name: The bucket name
    :param require_no_public_access:
                        If True the bucket must not have any public access.
                        Default True.
    :param require_encryption:
                        If True the bucket must have default encryption enabled.
                        Default True.
    :param require_server_logging:
                        If True the bucket must have default server logging
                        enabled. Default True.
    :param require_bucket_is_mine:
                        If True the bucket must belong to the current AWS
                        account. Default True.
    :param aws_session: A boto3 Session. If None a default is created.

    :return:            Nothing.

    :raise Exception:   If the bucket fails any of the security checks or the
                        status of any of the checks cannot be verified.

    """

    # Check bucket has no public access
    if require_no_public_access and s3_bucket_is_public(bucket_name, aws_session):
        raise Exception('Insecure due to public access')

    # Check bucket has default encryption enabled
    if require_encryption and not s3_bucket_is_encrypted(bucket_name, aws_session):
        raise Exception('Insecure due to lack of default encryption')

    # Check bucket has server logging enabled
    if require_server_logging and not s3_bucket_is_server_logging_enabled(bucket_name, aws_session):
        raise Exception('Insecure due to lack of server logging')

    # Check bucket belongs to the current AWS account
    if require_bucket_is_mine and not s3_bucket_is_mine(bucket_name, aws_session):
        raise Exception('Insecure due to foreign owned bucket')


# ------------------------------------------------------------------------------
def s3_bucket_is_server_logging_enabled(
    bucket_name: str, aws_session: boto3.Session = None
) -> bool:
    """
    Check if a bucket has server logging enabled.

    :param bucket_name: The bucket name
    :param aws_session: A boto3 Session. If None a default is created.

    :return:            True if the bucket has logging enabled.

    :raise Exception:   If the bucket doesn't exist or logging status cannot be
                        determined.
    """

    if not aws_session:
        aws_session = boto3.Session()

    s3 = aws_session.client('s3')

    try:
        return 'LoggingEnabled' in s3.get_bucket_logging(Bucket=bucket_name)
    except Exception as e:
        raise Exception(f'Cannot verify bucket has logging enabled - {e}')


# ------------------------------------------------------------------------------
def s3_bucket_is_encrypted(bucket_name: str, aws_session: boto3.Session = None) -> bool:
    """
    Check if a bucket has default encryption enabled.

    :param bucket_name: The bucket name
    :param aws_session: A boto3 Session. If None a default is created.

    :return:            True if the bucket has default encryption enabled.

    :raise Exception:   If the bucket doesn't exist or encryption status cannot
                        be determined.

    """

    if not aws_session:
        aws_session = boto3.Session()

    s3 = aws_session.client('s3')

    try:
        s3.get_bucket_encryption(Bucket=bucket_name)
        return True
    except ClientError as e:
        if 'ServerSideEncryptionConfigurationNotFoundError' in e.args[0]:
            return False
        raise Exception(f'Cannot verify bucket is encrypted - {e}')
    except Exception as e:
        raise Exception(f'Cannot verify bucket is encrypted - {e}')


# ------------------------------------------------------------------------------
def s3_bucket_is_public(bucket_name: str, aws_session: boto3.Session = None) -> bool:
    """
    Determine if a bucket has any public visibility.

    :param bucket_name: The bucket name
    :param aws_session: A boto3 Session. If None a default is created.

    :return:            True if there is any public access to the bucket.

    :raise Exception:   If the bucket doesn't exist or the ACL cannot be read.

    """

    if not aws_session:
        aws_session = boto3.Session()

    bucket = aws_session.resource('s3').Bucket(bucket_name)
    acl = bucket.Acl()

    for grant in acl.grants:
        # http://docs.aws.amazon.com/AmazonS3/latest/dev/acl-overview.html
        if (
            grant['Grantee']['Type'].lower() == 'group'
            and grant['Grantee']['URI'] == 'http://acs.amazonaws.com/groups/global/AllUsers'  # noqa
        ):
            return True

    return False


# ------------------------------------------------------------------------------
def s3_set_object_encoding(bucket: str, key: str, encoding: str, s3_client) -> None:
    """
    Set the Content-Encoding meta data for the given object to the given value.

    This requires copying the object onto itself. No copy is done if the content
    encoding is already correctly set.

    !!! warning
        This is actually doing an S3 object copy. Most of the obvious metadata and
        encryption settings are preserved but beware.

    !!! warning
        Because of the nature of S3, there is a potential race condition if you
        try to use the new object too quickly as S3 may not have finished
        the copy operation.

    :param bucket:      S3 bucket name.
    :param key:         Prefix of the object in the remote bucket.
    :param encoding:    New content encoding for t
    :param s3_client:   boto3 s3 client.

    """

    info = s3_client.head_object(Bucket=bucket, Key=key)
    if info.get('ContentEncoding') == encoding:
        return

    copy_args = {
        'Bucket': bucket,
        'Key': key,
        'CopySource': {'Bucket': bucket, 'Key': key},
        'ContentEncoding': encoding,
        'MetadataDirective': 'REPLACE',
    }

    # Preserve existing metadata, encryption etc
    for field in 'Metadata', 'ServerSideEncryption', 'SSEKMSKeyId', 'StorageClass':
        if info.get(field):
            copy_args[field] = info.get(field)

    s3_client.copy_object(**copy_args)


# ------------------------------------------------------------------------------
@static_vars(is_mine={})
def s3_bucket_is_mine(bucket_name: str, aws_session: boto3.Session = None) -> bool:
    """
    Determine if a bucket is owned by the current account.

    Requires IAM list buckets permission and access to the bucket ACL. Results
    are cached as buckets are not likely to change owning accounts.

    :param bucket_name: The bucket name
    :param aws_session: A boto3 Session. If None a default is created.

    :return:            True if the bucket is owned by the current account.

    :raise Exception:   If the bucket doesn't exist or the ownership cannot be
                        determined.

    """

    if not aws_session:
        aws_session = boto3.Session()

    if bucket_name not in s3_bucket_is_mine.is_mine:
        s3 = aws_session.client('s3')

        # Get the canonical ID for the current acccount
        canonical_id = s3.list_buckets()['Owner']['ID']

        bucket_owner = s3.get_bucket_acl(Bucket=bucket_name)['Owner']['ID']

        s3_bucket_is_mine.is_mine[bucket_name] = canonical_id == bucket_owner

    return s3_bucket_is_mine.is_mine[bucket_name]


# ------------------------------------------------------------------------------
def s3_object_exists(bucket: str, key: str, aws_session: boto3.Session = None) -> bool:
    """
    Check if an S3 object exists within an existing, accessible bucket.

    :param bucket:      Bucket name.
    :param key:         Object key.
    :param aws_session: A boto3 Session. If None, a default is created.
    :return:            True if the object exists. False if the bucket exists but
                        the object does not. An exception is raised if the bucket
                        does not exist.
    :raise ClientError: If the bucket does not exist or permissions prevent
                        access.
    """

    try:
        (aws_session or boto3.Session()).client('s3').head_object(Bucket=bucket, Key=key)
    except ClientError as e:
        if e.response['Error']['Code'] == '404':
            return False
        raise
    return True


# ..............................................................................
# endregion S3 utils
# ..............................................................................


# ..............................................................................
# region DynamoDB utils
# ..............................................................................


# ------------------------------------------------------------------------------
# Hope to convert DynamoDB types to Python
_DYNAMO_VALUE = {
    'S': lambda v: v,
    'SS': set,
    'BOOL': lambda v: v,
    'N': lambda v: float(v) if '.' in v else int(v),
    'NULL': lambda v: None,
    'B': b64decode,
    'BS': lambda v: {b64decode(vv) for vv in v},
    'NS': lambda v: {float(vv) if '.' in vv else int(vv) for vv in v},
    'M': lambda v: {kk: dynamo_unmarshall_value(vv) for kk, vv in v.items()},
    'L': lambda v: [dynamo_unmarshall_value(vv) for vv in v],
}


def dynamo_unmarshall_value(v: dict[str, Any]) -> Any:
    """
    Convert a DynamoDB structured value to a normal Python structure.

    Handles simple and compound types.

    For example, the following are typical conversions:

    ```python
    { 'S': 'abc' } --> 'abc'
    { 'BOOL': True } --> True
    { 'NULL': True } --> None
    { 'N': '99.9' } --> 99.9
    ```

    :param v:       The DynamoDB value.

    :return:        Python object

    """

    if not isinstance(v, dict) or len(v) != 1:
        raise ValueError(f'Bad DynamoDB JSON element: {v}')

    v_type = next(iter(v))
    v_val = v[v_type]

    try:
        return _DYNAMO_VALUE[v_type](v_val)
    except KeyError:
        raise ValueError(f'Unknown DynamoDB type: {v_type}')


# ------------------------------------------------------------------------------
def dynamo_unmarshall_item(item: dict[str, Any]) -> dict[str, Any]:
    """
    Convert a DynamoDB structured table item to a normal Python structure.

    :param item:    The DynamoDB item (as a Python object)


    :return:        Standard Python object.

    """

    if not isinstance(item, dict):
        raise ValueError(f'Bad DynamoDB data: expected dict but got {type(item)}')

    return {k: dynamo_unmarshall_value(v) for k, v in item.items()}


# ------------------------------------------------------------------------------
def dynamo_scan_table(table: str, aws_session: boto3.Session) -> Iterator[dict[str, Any]]:
    """
    Scan the specified DynamoDB table and return the items one at a time.

    :param table:           The table name.
    :param aws_session:     A boto3 Session().

    :return:                An iterator yielding items from the table.
    """

    dynamo = aws_session.client('dynamodb')
    paginator = dynamo.get_paginator('scan')

    response_iterator = paginator.paginate(TableName=table, Select='ALL_ATTRIBUTES')

    for response in response_iterator:
        for item in response['Items']:
            yield dynamo_unmarshall_item(item)


# ..............................................................................
# endregion DynamoDB utils
# ..............................................................................


# ..............................................................................
# region SES utils
# ..............................................................................


# ------------------------------------------------------------------------------
def ses_send(
    sender: str,
    to: str | Iterable[str] = None,
    cc: str | Iterable[str] = None,
    reply_to: str | Iterable[str] = None,
    return_path: str = None,
    subject: str = None,
    message: str = None,
    html: str = None,
    region: str = 'us-east-1',
    charset: str = 'UTF-8',
    config_set: str = None,
    aws_session: boto3.Session = None,
    bcc: str | Iterable[str] = None,
) -> None:
    """
    Send an email via SES.

    Note that SES is not available in all regions so we default to us-east-1.

    :param sender:      Sending email address. Must be verified or in a verified
                        domain.
    :param to:          Destination email address(es).
    :param cc:          Cc address(es).
    :param bcc:         Bcc address(es).
    :param reply_to:    Reply To address(es).
    :param return_path: Return path for bounces.
    :param subject:     Message subject.
    :param message:     Message text body. At least one of message and html
                        arguments needs to be supplied. Default None.
    :param html:        Message html body. At least one of message and html
                        arguments needs to be supplied. Default None.
    :param region:      Region for SES service. Defaults to us-east-1.
    :param charset:     The character set of the content. Default is 'UTF-8'.
    :param config_set:  Configuration set name.
    :param aws_session: A boto3 session object. If None a default session will
                        be created. Default None.

    :raise ValueError:  If neither message nor html are specified.

    """

    if not message and not html:
        raise ValueError('ses_send: One of html/message required')

    # ----------------------------------------
    # Handle addressing

    destination = {}
    if to:
        destination['ToAddresses'] = listify(to)
    if cc:
        destination['CcAddresses'] = listify(cc)
    if bcc:
        destination['BccAddresses'] = listify(bcc)

    # ----------------------------------------
    # Construct message body

    msg = {'Body': {}}

    if subject:
        msg['Subject'] = {'Data': subject, 'Charset': charset}

    if message:
        # noinspection PyTypeChecker
        msg['Body']['Text'] = {'Data': message, 'Charset': charset}

    if html:
        # noinspection PyTypeChecker
        msg['Body']['Html'] = {'Data': html, 'Charset': charset}

    # ----------------------------------------
    # Build sending args

    ses_args = {'Source': sender, 'Destination': destination, 'Message': msg}

    # ----------------------------------------
    # Supplementary fields

    if reply_to:
        ses_args['ReplyToAddresses'] = listify(reply_to)

    if return_path:
        ses_args['ReturnPath'] = return_path

    if config_set:
        ses_args['ConfigurationSetName'] = config_set

    # ----------------------------------------
    # Send the message

    if not aws_session:
        aws_session = boto3.Session()
    aws_session.client('ses', region_name=region).send_email(**ses_args)


# ..............................................................................
# endregion SES utils
# ..............................................................................


# ..............................................................................
# region CloudWatch utils
# ..............................................................................


# ------------------------------------------------------------------------------
def cw_put_metric(
    metric: str,
    namespace: str,
    dimensions: OrderedDict | list[dict[str, Any]],
    value: float | int,
    unit: str = 'None',
    resolution: str = 'low',
    cw_client=None,
) -> None:
    """
    Send metric data to CloudWatch.

    :param metric:      Metric name.
    :param namespace:   CloudWatch namespace. If None then this is a no-op.
    :param dimensions:  Either an ordered dict or a a list of dictionaries with
                        a single key/value
    :param value:       The metric value.
    :param unit:        The metric unit. If not specified the default of None
                        translates to CloudWatch 'None'.
    :param resolution:  Either 'hi'/'high' (1 second resolution or 'lo'/'low'
                        (1 minute resolution). Default is 'low'.
    :param cw_client:   CloudWatch client. If None then this is a no-op.

    """

    if not namespace or not cw_client:
        return

    if not unit:
        unit = 'None'

    # Convert dimensions to the format required by CloudWatch
    if isinstance(dimensions, OrderedDict):
        dim = [{'Name': k, 'Value': v} for k, v in dimensions.items()]
    elif isinstance(dimensions, list):
        dim = []
        for d in dimensions:  # type: dict
            if not isinstance(d, dict) or len(d) != 1:
                raise ValueError(f'Bad dimension for metric: {d}')
            dim.extend([{'Name': k, 'Value': v} for k, v in d.items()])
    else:
        raise ValueError(f'Bad type for metric dimensions: {type(dimensions)}')

    if not dim:
        raise ValueError('No dimensions for metric')

    metric_data = [
        {
            'MetricName': metric,
            'Dimensions': dim,
            'Timestamp': datetime.now(timezone.utc),
            'Value': value,
            'Unit': unit,
            'StorageResolution': 1 if resolution.lower().startswith('hi') else 60,
        }
    ]

    cw_client.put_metric_data(Namespace=namespace, MetricData=metric_data)


# ..............................................................................
# endregion CloudWatch utils
# ..............................................................................
