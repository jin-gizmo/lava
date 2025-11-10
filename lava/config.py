"""
Lava config.

App-wide defaults are set here.
"""

from __future__ import annotations

import logging
import os
from multiprocessing import cpu_count
from threading import Lock
from typing import Any

import boto3

from lava.lavacore import LOGNAME, get_realm_info
from lava.lib.decorators import static_vars

# ------------------------------------------------------------------------------
# General parameters

LOGLEVEL = os.environ.get('LAVA_LOGLEVEL', 'info')
LAVA_CODE_DIR = os.path.dirname(os.path.dirname(__file__))
LOG = logging.getLogger(name=LOGNAME)

# Arbitrary error status assigned to jobs that timeout
STATUS_TIMEOUT = 28

__realm_info__ = None
__config__ = {
    'TMPDIR': '/tmp/lava',  # noqa: S108
    'HEARTBEAT_FILE': '.heartbeat',  # Relative to TMPDIR
    'DISPATCHER': '/usr/local/bin/lava-dispatcher',
    'NO_DISPATCH': '/tmp/lava/__nodispatch__',  # noqa: S108
    'SQS_MAX_DELAY_MINS': 15,  # Maximum allowed delay for an SQS message
    'EVENT_TTL': '2d',  # TTL for event records in DynamoDB. None means disable.
    'STDERR_SIZE': 2000,  # Read this many bytes for error messages. If -ve read from end.
    'DEBUG': False,  # Enable some debugging type things.
    'CW_NAMESPACE': 'Lava',  # Namespace for CloudWatch metrics
    'CW_METRICS_JOB': False,  # If True send job metrics to CloudWatch
    'CW_METRICS_WORKER': False,  # If True send internal metrics to CloudWatch.
    'CW_METRICS_PERIOD': '1m',  # Period for pushing internal metrics.
    'JOB_LOCAL_TMPDIR': True,  # Job tmp area is in its private run area.
    'ITERATION_MAX_DELAY': '5m',  # Maximum allowed delay when rerunning a failed job.
    'ITERATION_MAX_LIMIT': 10,  # Maximum number of runs allowed for a job.
    'PARAM_CACHE_SIZE': 100,  # SIze of the SSM parameter cache
    'PARAM_CACHE_TTL': '2m',  # Cache SSM parameter values for this duration.
    'PAYLOAD_DOWNLOADER': 'v2',  # Which payload downloader should we use?
    'PAYLOAD_SETTLING_TIME': 1,  # Seconds to wait before using a downloaded payload.
    'CHECK_FOR_ZOMBIES': True,  # On exit, try to prevent zombie threads from blocking.
    'JUMPSTART_DELAY': '15s',  # Give the worker a little time to fully initialise.
    # . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . .
    # dag handler constraints
    'DAG_MAX_WORKERS': cpu_count() * 4,  # Maximum allowed worker count for dag jobs.
    'DAG_WORKERS': cpu_count(),  # Default worker count for dag jobs.
    # . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . .
    # sql / sqli handler constants
    'SQL_BATCH_SIZE': 1024,  # Number of rows to fetch in one go.
    'SQL_DELIMITER': '|',
    'SQL_DIALECT': 'excel',
    'SQL_DOUBLEQUOTE': False,
    'SQL_ESCAPECHAR': None,
    'SQL_MAX_PAYLOAD_SIZE': '100K',  # Limit SQL size
    'SQL_OUTPUT_SUFFIX': '.out',
    'SQL_QUOTECHAR': '"',
    'SQL_QUOTING': 'minimal',
    # . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . .
    # Sqlc handler constants
    'SQLC_MAX_PAYLOAD_SIZE': '100K',  # Limit SQL size
    'SQLC_TIMEOUT': '10m',  # Run timeout for sqlc jobs
    # . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . .
    # Sqlv specific handler constants. Mostly SQL_* constants apply.
    'SQLV_TIMEOUT': '10m',  # Run timeout for sqlv jobs
    # . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . .
    # SMB handler constants
    'SMB_TIMEOUT': '10m',  # Run timeout for smb jobs
    # . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . .
    # Exe handler constants
    'EXE_MAX_PAYLOAD_SIZE': '10M',  # Limit payload size
    'EXE_TIMEOUT': '10m',  # Run timeout for the exe
    # . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . .
    # Cmd handler constants
    'CMD_TIMEOUT': '10m',  # Run timeout for the command
    # . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . .
    # Pkg handler constants
    'PKG_MAX_PAYLOAD_SIZE': '20M',
    'PKG_TIMEOUT': '10m',  # Run timeout for the job
    'PKG_UNPACK_TIMEOUT': '30s',  # Unpack timeout for the job
    # . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . .
    # Docker handler constants
    'DOCKER_TIMEOUT': '10m',  # Run timeout for the container run
    # . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . .
    # AWS SES constants
    'SES_CONFIGURATION_SET': None,
    'SES_REGION': 'us-east-1',
    'SES_FROM': None,  # Set to a string which is source email address
    # . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . .
    # Email constants (not SES specific)
    'EMAIL_MAX_ATTACHMENTS': 5,  # Limit number of attachments - zero disables attachments.
    'EMAIL_MAX_ATTACHMENT_SIZE': '2M',
    'EMAIL_MAX_SIZE': '5M',
    # . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . .
    # Postgres client side copy timeout.
    'PG_COPY_TIMEOUT': '30m',
    # . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . .
    # SharePoint job constants
    'SP_LIST_DELIMITER': '|',
    'SP_LIST_DOUBLEQUOTE': False,
    'SP_LIST_ESCAPECHAR': None,
    'SP_LIST_QUOTECHAR': '"',
    'SP_LIST_QUOTING': 'minimal',
    'SP_LOGGING': False,
    # . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . .
    'FOREACH_LIMIT': 10,  # Unless job overrides, this is the max foreach length.
    'FOREACH_MAX_LIMIT': 25,  # Max value a job can set for limit.
    # . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . .
    # s3trigger config
    'S3TRIGGER_CACHE_TTL': '60s',  # s3trigger table lookups are cached
    'S3TRIGGER_DEDUP_TTL': '30s',  # s3trigger bucket/key caching.
    'S3TRIGGER_DEDUP_CACHE_SIZE': 0,  # s3trigger bucket/key caching.
    # . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . .
    # Redshift specific config
    'RS_PASSWORD_DURATION': '15m',  # For GetClusterCredentials
    # . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . .
    # State management config
    'STATE_MAX_TTL': '366d',
    'STATE_TTL': '7d',
    # . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . .
    # Connector config
    'AWS_CONN_DURATION': '3h',
    'AWS_ACCESS_KEY_CACHE_TTL': '10m',
    'AWS_ACCESS_KEY_CACHE_SIZE': 20,
    'CONN_APP_NAME': 'lv-{{ realm }}-{{ job_id }}',  # Jinja template. See make_application_name()
}


# ------------------------------------------------------------------------------
def config_update(c: dict[str, Any]) -> None:
    """
    Update the config.

    :param c:           A dictionary of config items that is overlaid on the
                        base config. Keys are converted to upper case.
    """

    __config__.update({k.upper(): v for k, v in c.items()})


# ------------------------------------------------------------------------------
@static_vars(realm_info=None)
def config_load(realm: str, aws_session: boto3.Session = None) -> dict[str, Any]:
    """
    Load the realm config from the realms table. Only ever done once.

    :param realm:       Realm name.
    :param aws_session: A boto3 session. A default session will be created
                        if needed.

    :return:            The realm entry from the realms table
    """

    with Lock():
        # Only load once
        if config_load.realm_info:
            return config_load.realm_info

        if not aws_session:
            aws_session = boto3.Session()
        try:
            realm_table = aws_session.resource('dynamodb').Table('lava.realms')
        except Exception as e:
            raise Exception(f'Cannot get DynamoDB table lava.realms - {e}')

        realm_info = get_realm_info(realm, realm_table)
        config_load.realm_info = realm_info
        config_update(realm_info.get('config', {}))

        LOG.debug(f'Loaded config: {__config__}')

    return realm_info


# ------------------------------------------------------------------------------
def config(key: str, convert=None) -> Any:
    """
    Return the value of the named config item.

    For a key of 'xyz', the first of the following to be found is returned:

    -   The environment variable LAVA_XYZ.
    -   The _config[XYZ] defined in this file.

    :param key:         The config item name.
    :param convert:     The value will be passed through the converter runnable
                        to process it (e.g. to cast it to a given type). If not
                        specified no conversion is performed.

    :return:            The config item value.

    :raise KeyError: If the key cannot be found.
    """

    key = key.upper()

    try:
        v = os.environ['LAVA_' + key]
    except KeyError:
        v = __config__[key]

    try:
        return convert(v) if convert else v
    except ValueError:
        raise Exception(f'Cannot convert config item {key} using {convert}')
