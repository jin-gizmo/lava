"""
Lambda function to calculate CloudWatch metrics.

These are ones that it doesn't make sense for an individual worker to produce.

Current list:

-   MessageBacklogPerWorker

Intention is for this to run on a 1 minute timer.

"""

from __future__ import annotations

import logging
import os
from contextlib import suppress
from pprint import pformat
from threading import RLock
from typing import Any

import boto3
from cachetools import TTLCache, cached

from lava.config import LOGLEVEL, LOGNAME, config
from lava.lib.logging import get_log_level

__author__ = 'Murray Andrews'

# If LOGNAME is set to None you get all the boto3 events as well.
LOG = logging.getLogger(name=LOGNAME)

PROG = 'metrics'

METRIC_BACKLOG = 'WorkerBacklog'

# Duration on our TTL cache for SQS queue listing
QLIST_CACHE_TTL = 1200  # seconds
QLIST_CACHE_SIZE = 10


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
@cached(
    TTLCache(maxsize=QLIST_CACHE_SIZE, ttl=QLIST_CACHE_TTL),
    lock=RLock(),
    key=lambda queue_prefix, _: queue_prefix,
)
def sqs_list_queues(queue_prefix: str, sqs_client) -> list[str]:
    """
    Get a list of SQS queue URLs for queues with a given name prefix.

    Results are cached for 20 minutes.

    :param queue_prefix:    Queue name prefix.
    :param sqs_client:      boto3 SQS client.
    :return:                A list of queue URLs.
    """

    urls = []
    paginator = sqs_client.get_paginator('list_queues')
    for response in paginator.paginate(QueueNamePrefix=queue_prefix):
        with suppress(KeyError):
            urls.extend(response['QueueUrls'])

    return urls


# ------------------------------------------------------------------------------
def sqs_queue_depth_by_worker(realm: str, aws_session: boto3.Session = None) -> dict[str, int]:
    """
    Get the worker queue depth for each worker in the realm.

    SQS queues must be named `lava-<REALM>-<WORKER>`

    :param realm:       Lava realm name.
    :param aws_session: A boto3 Session().
    :return:            A dict. Keys are worker names. Values SQS queue depth.
    """

    if not aws_session:
        aws_session = boto3.Session()
    sqs = aws_session.client('sqs')

    queue_prefix = f'lava-{realm}-'
    queue_info = {}

    for url in sqs_list_queues(queue_prefix, sqs):
        worker = url.rsplit('/', 1)[-1]
        try:
            queue_info[worker] = int(
                sqs.get_queue_attributes(
                    QueueUrl=url, AttributeNames=['ApproximateNumberOfMessages']
                )['Attributes']['ApproximateNumberOfMessages']
            )
        except KeyError as e:
            LOG.warning('Worker %s: key error %s', worker, e)
        except Exception as e:
            LOG.error('Worker %s: %s', worker, e)

    return queue_info


# ------------------------------------------------------------------------------
def asg_active_workers(names: list[str], aws_session: boto3.Session = None) -> dict[str, int]:
    """
    Get the number of in-service lava workers in specified auto scaling groups.

    :param names:       Auto scaling group names.
    :param aws_session: A boto3 Session.
    :return:            A dict. Keys are ASG name. Values are instance counts.
                        Non existent ASGs will be ignored.
    """

    if not aws_session:
        aws_session = boto3.Session()
    autoscale = aws_session.client('autoscaling')

    asg_info = {}

    paginator = autoscale.get_paginator('describe_auto_scaling_groups')
    for response in paginator.paginate(AutoScalingGroupNames=names):
        for asg in response.get('AutoScalingGroups', []):
            asg_info[asg['AutoScalingGroupName']] = sum(
                1 for instance in asg['Instances'] if instance['LifecycleState'] == 'InService'
            )

    return asg_info


# ------------------------------------------------------------------------------
def metric_backlog_per_worker(realm: str, aws_session: boto3.Session = None) -> None:
    """
    Create a CloudWatch metric `BacklogPerWorker` for each auto scaling group.

    `BacklogPerWorker` is defined as SQS queue depth / # InService workers. No
    metric value is generated if # InService workers is zero.

    :param realm:       Lava realm name.
    :param aws_session: A boto3 Session().
    """

    if not aws_session:
        aws_session = boto3.Session()
    cwatch = aws_session.client('cloudwatch')

    queue_depths = sqs_queue_depth_by_worker(realm, aws_session=aws_session)
    worker_count = asg_active_workers(list(queue_depths), aws_session=aws_session)
    name_offset = len(f'lava-{realm}-')
    backlog_per_worker = {
        w[name_offset:]: round(queue_depths[w] / n, 1) for w, n in worker_count.items() if n > 0
    }

    metric_data = [
        {
            'MetricName': METRIC_BACKLOG,
            'Dimensions': [
                {'Name': 'Realm', 'Value': realm},
                {'Name': 'Worker', 'Value': worker},
            ],
            'Value': backlog,
        }
        for worker, backlog in backlog_per_worker.items()
    ]

    LOG.info('Backlog metric data:\n%s', pformat(metric_data))

    if metric_data:
        cwatch.put_metric_data(Namespace=config('CW_NAMESPACE'), MetricData=metric_data)


# ------------------------------------------------------------------------------
def lambda_handler(event: dict[str, Any], context) -> None:
    """
    AWS lambda entry point.

    :param event:       Lambda event data.
    :param context:     Lambda context. This will be populated if running in
                        lambda but None if running in an eventworker.
    :type event:        dict

    """

    setup_logging(os.environ.get('LOGLEVEL', LOGLEVEL), name=LOGNAME)
    if LOGLEVEL == 'debug':
        # pformat() is a bit expensive so we guard it
        LOG.debug('Received event: %s', pformat(event))

    realm = os.environ.get('LAVA_REALM')
    if realm != realm_from_lava_id(context.function_name):
        raise Exception('Lava configuration error: realm name mismatch')

    aws_session = boto3.Session()

    try:
        metric_backlog_per_worker(realm, aws_session=aws_session)
    except Exception as e:
        LOG.error('Backlog metric failed: %s', e)
        raise
