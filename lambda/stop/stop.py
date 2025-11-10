"""
Lambda function to assist with controlled shutdown of worker nodes.

This is intended to receive auto scaling lifecycle hook terminating events from
EventBridge. It then executes SSM Run Command with AWSRunShellScript to run the
on-board `lava-stop` command. Yeah, I know.

These events look like this:

..code :: json

  {
    "LifecycleActionToken": "57ccc575-b75f-4d44-a718-75b42d9241a5",
    "AutoScalingGroupName": "lava-dev-core",
    "LifecycleHookName": "terminating",
    "EC2InstanceId": "i-00c47b9667d9218af",
    "LifecycleTransition": "autoscaling:EC2_INSTANCE_TERMINATING",
    "NotificationMetadata": "...",
    "Origin": "AutoScalingGroup",
    "Destination": "EC2"
  }

"""

from __future__ import annotations

import logging
import os
from pprint import pformat
from shlex import quote
from typing import Any

import boto3

from lava.config import LOGLEVEL, LOGNAME
from lava.lib.logging import get_log_level
from lava.lib.misc import dict_check

__author__ = 'Murray Andrews'

# If LOGNAME is set to None you get all the boto3 events as well.
LOG = logging.getLogger(name=LOGNAME)

PROG = 'stop'

STOP_COMMAND = 'lava-stop'
# Allow the node this long to shutdown gracefully
WAIT_TIME = os.environ.get('WAIT_TIME', '2m')
# Signal the ASG
LIFECYCLE_HEARTBEAT = os.environ.get('LIFECYCLE_HEARTBEAT', '1m')
# Seconds to start
COMMAND_TIMEOUT = 60


# ------------------------------------------------------------------------------
def setup_logging(level: str, name: str = None) -> None:
    """
    Set up logging.

    :param level:   Logging level. The string format of a level (eg 'debug').
    :param name:    Logger name. Default None implies root logger.

    """

    logger = logging.getLogger(name)
    logger.setLevel(get_log_level(level))
    logger.debug('Log level set to %s (%d)', level, logger.getEffectiveLevel())


# ------------------------------------------------------------------------------
def realm_from_lava_id(lava_id: str) -> str:
    """
    Extract the realm name from a lava identifier.

    :param lava_id:     A lava identifier in the form `lava-<REALM>-*`
    :return:            The realm name.

    :raise ValueError:  If malformed lava ID.
    """

    try:
        lava, realm, *_ = lava_id.split('-')
    except ValueError:
        raise ValueError(f'Bad lava identifier: {lava_id}')

    if lava != 'lava' or not realm:
        raise ValueError(f'Bad lava identifier: {lava_id}')

    return realm


# ------------------------------------------------------------------------------
def lambda_handler(event: dict[str, Any], context) -> None:
    """
    AWS lambda entry point.

    :param event:       Lambda event data.
    :param context:     Lambda context. This will be populated if running in
                        lambda but None if running in an eventworker.
    :type event:        dict

    """

    loglevel = os.environ.get('LOGLEVEL', LOGLEVEL)
    setup_logging(loglevel, name=LOGNAME)
    LOG.info('Received event: %s', pformat(event))

    dict_check(event, required={'EC2InstanceId'})

    aws_session = boto3.Session()
    ssm = aws_session.client('ssm')

    instance_id = event['EC2InstanceId']

    command = [
        'nohup',
        STOP_COMMAND,
        '--no-dispatch',  # Stop the dispatchers on the node while daemons are stopping
        '--signal',
        'SIGHUP',
        '--instance-id',
        quote(instance_id),
        '--log @local0',
        '--level',
        quote(LOGLEVEL),
        '--wait',
        quote(WAIT_TIME),
    ]

    asg_name = event.get('AutoScalingGroupName')
    if asg_name:
        if not (
            os.environ.get('LAVA_REALM')
            == realm_from_lava_id(asg_name)
            == realm_from_lava_id(context.function_name)
        ):
            raise Exception('Lava configuration error: realm name mismatch')
        command.extend(['--auto-scaling-group-name', quote(event['AutoScalingGroupName'])])
        command.extend(['--lifecycle-heartbeat', quote(LIFECYCLE_HEARTBEAT)])

    if event.get('LifecycleActionToken'):
        command.extend(['--lifecycle-action-token', quote(event['LifecycleActionToken'])])

    if event.get('LifecycleHookName'):
        command.extend(['--lifecycle-hook-name', quote(event['LifecycleHookName'])])

    command.append('> /tmp/lava/__stop__ 2>&1 &')

    prepared_command = ' '.join(command)
    LOG.info('Command: %s', prepared_command)

    try:
        response = ssm.send_command(
            InstanceIds=[instance_id],
            DocumentName='AWS-RunShellScript',
            TimeoutSeconds=COMMAND_TIMEOUT,
            Comment='lava-stop',
            CloudWatchOutputConfig={'CloudWatchOutputEnabled': True},
            Parameters={'commands': [prepared_command]},
        )
    except Exception as e:
        LOG.error('SendCommand failed: %s', e)
        raise

    LOG.info('Response:\n%s', pformat(response))

    # ----------------------------------------
    LOG.info('Event %s: Completed', context.aws_request_id)
