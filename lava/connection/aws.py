"""Lava connector for AWS resources."""

from __future__ import annotations

import json
import os
from contextlib import suppress
from stat import S_IRUSR, S_IWUSR, S_IXUSR
from tempfile import mkdtemp
from threading import RLock
from typing import Any

import boto3
from cachetools import TTLCache, cached

from lava.common import get_lava_param
from lava.config import config
from lava.lavacore import IGNORE_FIELDS, LavaError
from lava.lib.aws import ssm_get_param
from lava.lib.datetime import duration_to_seconds
from lava.lib.misc import clean_str, dict_check, listify
from .core import (
    CONNECTION_OPTIONAL_FIELDS,
    CONNECTION_REQUIRED_FIELDS,
    LOG,
    cli_connector,
    get_connection_spec,
    make_application_name,
)

__author__ = 'Murray Andrews'

AWS_CONNECTION_REQUIRED_FIELDS = CONNECTION_REQUIRED_FIELDS
AWS_CONNECTION_OPTIONAL_FIELDS = CONNECTION_OPTIONAL_FIELDS | {
    'access_keys',
    'role_arn',
    'external_id',
    'duration',
    'policy_arns',
    'policy',
    'region',
    'tags',
}

ROLE_SESSION_NAME_MAX_LEN = 64  # AWS limit


# ------------------------------------------------------------------------------
def _get_access_keys_from_ssm(ssm_param_name, aws_session: boto3.Session = None) -> dict[str, str]:
    """
    Get static access keys from an SSM parameter.

    The access keys must be stored as `access_key_id,access_secret_key`.

    :param ssm_param_name:  Name of the (secure) SSM parameter.
    :param aws_session:     A boto3 Session(). If not specified a default
                            session is created.
    :return:
    """

    # Get the access keys from SSM - must be access_key_id,secret_access_key
    try:
        access_keys = get_lava_param(ssm_param_name, aws_session=aws_session)
    except Exception as e:
        raise LavaError(f'SSM {ssm_param_name}: {e}')

    try:
        aws_access_key_id, aws_secret_access_key = access_keys.split(',', 1)
    except ValueError:
        raise LavaError(
            f'SSM {ssm_param_name}: Must be in format "access_key_id,access_secret_key"'
        )

    return {
        'aws_access_key_id': aws_access_key_id,
        'aws_secret_access_key': aws_secret_access_key,
    }


# ------------------------------------------------------------------------------
def assume_role(
    role_arn: str,
    role_session_name: str,
    external_id_ssm_param: str = None,
    duration: str = None,
    policy_arns: str | list[str] = None,
    policy: dict[str, Any] = None,
    tags: dict[str, Any] = None,
    aws_session: boto3.Session = None,
) -> dict[str, str]:
    """
    Assume an IAM role.

    :param role_arn:            ARN of role to assume.
    :param role_session_name:   Role session name. This will be cleansed to
                                ensure it only contains chars STS will accept.
    :param external_id_ssm_param: Name of SSM parameter containing external ID.
                                If not specified, no external ID is used.
    :param duration:            Duration for the assumed role session as a
                                duration string. If not specified, the value
                                specified by the `AWS_CONN_DURATION` config
                                variable is used.
    :param policy_arns:         ARN(s) of managed policies to use as managed
                                session policies.
    :param policy:              IAM policy to use as an inline session policy.
    :param tags:                Session tags.
    :param aws_session:         A boto3 Session(). If not specified a default is
                                created.
    :return:            A dict containing `aws_access_key_id`, `aws_secret_access_key`
                        and `aws_session_token`.
    """

    if not aws_session:
        aws_session = boto3.Session()

    assume_role_args = {
        'RoleArn': role_arn,
        'RoleSessionName': clean_str(role_session_name, safe_chars='=,.@-', alternative='.')[
            :ROLE_SESSION_NAME_MAX_LEN
        ],
        'DurationSeconds': int(duration_to_seconds(duration or config('AWS_CONN_DURATION'))),
    }

    if external_id_ssm_param:
        try:
            assume_role_args['ExternalId'] = ssm_get_param(
                external_id_ssm_param, aws_session=aws_session
            )
        except Exception as e:
            raise LavaError(f'SSM parameter {external_id_ssm_param}: {e}')
    if policy_arns:
        assume_role_args['PolicyArns'] = [{'arn': arn} for arn in listify(policy_arns)]
    if policy:
        assume_role_args['Policy'] = json.dumps(policy)
    if tags:
        assume_role_args['Tags'] = [{'Key': k, 'Value': v} for k, v in tags.items()]

    sts = aws_session.client('sts')
    creds = sts.assume_role(**assume_role_args)['Credentials']

    return {
        'aws_access_key_id': creds['AccessKeyId'],
        'aws_secret_access_key': creds['SecretAccessKey'],
        'aws_session_token': creds['SessionToken'],
    }


# ------------------------------------------------------------------------------
# The caching appraach here is a bit lazy in that we just cache for a relatively
# short period of time. This should be more than sufficient to take pressure off
# IAM in the event of a flurry of jobs using the same connector. A more
# sophisticated appraoch would be to cache static keys for a small amount of time
# (in case they are modified) and each session access key for a period of time
# that is dependent on the expiry time of individual keys that still leaves a
# reasonable TTL on the keys. Much too complicated for too little value.


@cached(
    TTLCache(
        maxsize=config('AWS_ACCESS_KEY_CACHE_SIZE', int),
        ttl=config('AWS_ACCESS_KEY_CACHE_TTL', duration_to_seconds),
    ),
    lock=RLock(),
    key=lambda conn_spec, *_, **__: conn_spec['conn_id'],
)
def _get_aws_credentials(
    conn_spec: dict[str, str], aws_session: boto3.Session = None
) -> dict[str, str]:
    """
    Get AWS credentials using info in an aws connection spec.

    :param conn_spec:   Connection specification
    :param aws_session: A boto3 Session(). If not specified, a default
                        session is created.
    :return:            A dict containing `aws_access_key_id`, `aws_secret_access_key`
                        `aws_session_token` (conditional) and `region`.
    """

    conn_id = conn_spec['conn_id']
    LOG.debug('Getting AWS credentials for conn_id %s', conn_id)
    conn_type = conn_spec.get('type', '').lower()
    if conn_type != 'aws':
        raise LavaError(f'Connection {conn_id}: Must be of type "aws" not "{conn_type}"')
    if not aws_session:
        aws_session = boto3.Session()

    try:
        dict_check(
            conn_spec,
            required=AWS_CONNECTION_REQUIRED_FIELDS,
            optional=AWS_CONNECTION_OPTIONAL_FIELDS,
            ignore=IGNORE_FIELDS,
        )
    except Exception as e:
        raise LavaError(f'Connection {conn_id}: {e}')

    if not conn_spec['enabled']:
        raise LavaError(f'Connection {conn_id}: Not enabled')

    if 'access_keys' in conn_spec:
        try:
            conn_info = _get_access_keys_from_ssm(conn_spec['access_keys'], aws_session=aws_session)
        except Exception as e:
            raise LavaError(f'SSM {conn_spec["access_keys"]}: {e}')

    elif 'role_arn' in conn_spec:
        # Assume a role
        conn_info = assume_role(
            role_arn=conn_spec['role_arn'],
            role_session_name=make_application_name(conn_id=conn_id) or 'lava',
            external_id_ssm_param=conn_spec.get('external_id'),
            duration=conn_spec.get('duration'),
            policy_arns=conn_spec.get('policy_arns'),
            policy=conn_spec.get('policy'),
            tags=conn_spec.get('tags'),
            aws_session=aws_session,
        )
    else:
        # Get session creds
        raise LavaError(f'Connection {conn_id}: One of access_keys or role_arn is required')

    return {'region': conn_spec.get('region', aws_session.region_name)} | conn_info


# ------------------------------------------------------------------------------
def get_aws_connection(
    conn_id: str, realm: str, aws_session: boto3.Session = None
) -> dict[str, str]:
    """
    Extract a set of AWS access credentials from the connections table.

    It is up to the caller to do something useful with those (e.g. create a
    boto3 Session()).

    This supports conventional access keys as well as the option of assuming an
    IAM role, including cross-account roles.

    !!! note
        The `get_aws_connection` naming is a bit of poetic licence, as it
        doesn't actually *connect* to anything. In most cases
        [get_aws_session][lava.connection.get_aws_session] is a better option.

    :param conn_id:         Connection ID.
    :param realm:           Realm
    :param aws_session:     A boto3 Session(). If not specified, a default
                            session is created.

    :return:        A dict containing `aws_access_key_id`, `aws_secret_access_key`
                    `aws_session_token` (conditional) and `region`.
    """

    # ----------------------------------------
    # Get the connection spec and make sure its ok

    if not aws_session:
        aws_session = boto3.Session()

    conn_spec = get_connection_spec(conn_id, realm, aws_session=aws_session)
    # The @cached decorator confuses PyCharm
    # noinspection PyCallingNonCallable
    return _get_aws_credentials(conn_spec, aws_session=aws_session)


# ------------------------------------------------------------------------------
def get_aws_session(conn_id: str, realm: str, aws_session: boto3.Session = None) -> boto3.Session:
    """
    Get a boto3 session based on the details specified in a lava AWS connection.

    This supports conventional access keys as well as the option of assuming an
    IAM role, including cross-account roles.

    :param conn_id:         Connection ID.
    :param realm:           Realm
    :param aws_session:     A boto3 Session() used to access the local AWS
                            environment. If not specified, a default session is
                            created.
    :return:                A boto3 Session().
    """

    aws_creds = get_aws_connection(conn_id, realm, aws_session=aws_session)

    session_args = {
        'aws_access_key_id': aws_creds['aws_access_key_id'],
        'aws_secret_access_key': aws_creds['aws_secret_access_key'],
        'region_name': aws_creds['region'],
    }

    with suppress(KeyError):
        session_args['aws_session_token'] = aws_creds['aws_session_token']

    return boto3.Session(**session_args)


# ------------------------------------------------------------------------------
@cli_connector('aws')
def cli_connect_aws(conn_spec: dict[str, Any], workdir: str, aws_session: boto3.Session = None):
    """
    Generate a CLI command to run the AWS CLI with lava managed access keys.

    :param conn_spec:       Connection specification
    :param workdir:         Working directory name.
    :param aws_session:     A boto3 Session(). This is used to get credentials
                            but is not used in the connector iteself.

    :return:                Name of an executable that implements the connection.

    """

    # The @cached decorator confuses PyCharm
    # noinspection PyCallingNonCallable
    aws_creds = _get_aws_credentials(conn_spec, aws_session=aws_session)
    conn_dir = mkdtemp(dir=workdir, prefix='conn.')

    # Create an AWS config file
    aws_config_preamble = """
[profile lava]
s3 =
    signature_version = s3v4
    """
    conf_file = os.path.join(conn_dir, '.aws_config')
    with open(conf_file, 'w') as fp:
        print(aws_config_preamble, file=fp)
        for k, v in aws_creds.items():
            print(f'{k}={v}', file=fp)
    os.chmod(conf_file, S_IRUSR | S_IWUSR)
    LOG.debug('Created %s', conf_file)

    # Create a little shell script that implements the connection.
    conn_script = f'#!/bin/bash\n\nAWS_CONFIG_FILE={conf_file} aws --profile lava "$@"'
    LOG.debug('AWS cli script is %s', conn_script)

    conn_cmd_file = os.path.join(conn_dir, 'aws')
    with open(conn_cmd_file, 'w') as fp:
        print(conn_script, file=fp)
    os.chmod(conn_cmd_file, S_IRUSR | S_IWUSR | S_IXUSR)

    LOG.debug('Created %s', conn_cmd_file)

    return conn_cmd_file
