"""Dummy handler that just logs the job request."""

from __future__ import annotations

import json
import logging
from typing import Any

import boto3

from lava.config import LOGNAME
from lava.lib.misc import json_default

__author__ = 'Murray Andrews'

LOG = logging.getLogger(name=LOGNAME)


# ------------------------------------------------------------------------------
# noinspection PyUnusedLocal
def run(
    job_spec: dict[str, Any],
    realm_info: dict[str, Any],
    tmpdir: str,
    s3tmp: str,
    dev_mode: bool = False,
    aws_session: boto3.Session = None,
) -> dict[str, Any]:
    """
    Log the job specification at level ``INFO``.

    :param job_spec:        The job spec from the DynamoDB database.
    :param realm_info:      Realm specific parameters.
    :param tmpdir:          A local temporary directory.
    :param s3tmp:           A prefix in S3 where temporary assets can be created
                            and left for others to pick up for limited time.
    :param dev_mode:        Not used for this handler.
    :param aws_session:     A boto3 Session()

    :return:                A dictionary of parameters that are available to
                            on-success, on-error, on-retry handlers.

    """

    LOG.info(
        json.dumps(job_spec, indent=4, sort_keys=True, default=json_default),
        extra={'event_type': 'job', 'job_id': job_spec['job_id'], 'run_id': job_spec['run_id']},
    )

    return {'exit_status': 0}
