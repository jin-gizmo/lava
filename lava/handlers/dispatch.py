"""Handler to dispatch another job."""

from __future__ import annotations

import json
import logging
from typing import Any

import boto3
import jinja2
from dateutil.tz import UTC

from lava.config import LOGNAME, config
from lava.lavacore import LavaError, dispatch, jinja_render_vars
from lava.lib.datetime import duration_to_seconds
from lava.lib.misc import dict_check, json_default

__author__ = 'Murray Andrews'

LOG = logging.getLogger(name=LOGNAME)

JOB_PARAMS_REQUIRED_FIELDS = set()
JOB_PARAMS_OPTIONAL_FIELDS = {'parameters', 'delay', 'jinja', 'job_prefix'}


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
    Dispatch another lava job.

    The payload is a comma separated list, or a real list of job IDs to
    dispatch.

    Allowed job parameters are:

    - jinja
        An optional boolean indicating whether Jinja rendering is enabled.
        Default True.

    - parameters
        An optional dictionary of parameters that will be sent with the
        dispatch. It is rendered using Jinja2 with the job spec, realm info and
        job result data being injected.

    - delay
        An optional duration string specifying a delay in the dispatch message.
        Must be <=15 min

    Any job parameters are included as parameters in the dispatch
    messages.

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

    parameters = job_spec.get('parameters', {})
    try:
        dict_check(
            parameters, required=JOB_PARAMS_REQUIRED_FIELDS, optional=JOB_PARAMS_OPTIONAL_FIELDS
        )
    except ValueError as e:
        raise LavaError(f'Bad job parameters: {e}')

    params = parameters.get('parameters')  # Yes -- parameters inside parameters
    enable_jinja = parameters.get('jinja', True)

    if params and enable_jinja:
        # Render parameters. This is a bit of a hack wehere we JSON serialise,
        # render then deserialise.
        try:
            params = json.loads(
                jinja2.Template(json.dumps(params, indent=2, default=json_default)).render(
                    **jinja_render_vars(job_spec, realm_info)
                )
            )
        except Exception as e:
            raise LavaError(f'Cannot render parameters - {e}')

        LOG.debug('Dispatch handler rendered params: %s', params)

    sqs_max_delay_mins = config('SQS_MAX_DELAY_MINS', int)
    delay = parameters.get('delay')

    try:
        delay = int(duration_to_seconds(parameters.get('delay', 0)))
        if not 0 <= delay <= sqs_max_delay_mins * 60:
            raise ValueError(f'must be between 0 and {sqs_max_delay_mins} minutes')
    except Exception as e:
        raise LavaError(f'Bad delay: {delay}: {e}')

    # ----------------------------------------
    # Unpack the list of jobs to dispatch
    job_list = job_spec['payload']
    if isinstance(job_list, str):
        job_list = [j.strip() for j in job_list.split(',')]
    elif not isinstance(job_list, list):
        raise LavaError('Payload must be comma separated list or real list of job IDs')

    if job_prefix := parameters.get('job_prefix', ''):
        job_list = [f'{job_prefix}{job_id}' for job_id in job_list]

    # ----------------------------------------
    # Dispatch them
    return_info = {'exit_status': 0, 'jobs': []}

    # Configure globals for the child jobs. We distinguish between the master
    # job which is at the top of the tree and the parent job which is the
    # immediate parent.  master_* vars are already set at this point.

    lava_globals = job_spec['globals']['lava']  # type: dict
    lava_globals['parent_job_id'] = job_spec['job_id']
    lava_globals['parent_start'] = job_spec['ts_start'].isoformat()
    lava_globals['parent_ustart'] = job_spec['ts_start'].astimezone(UTC).isoformat()

    for target_job_id in job_list:
        return_info['jobs'].append(target_job_id)

        if target_job_id == job_spec['job_id']:
            return_info['exit_status'] = 1
            return_info['error'] = f'{target_job_id}: Circular dispatch not permitted'
            raise LavaError(return_info['error'], data=return_info)

        try:
            dispatch(
                realm=realm_info['realm'],
                job_id=target_job_id,
                params=params,
                globals_=job_spec['globals'],
                delay=delay,
                aws_session=aws_session,
            )
        except Exception as e:
            return_info['exit_status'] = 1
            return_info['error'] = f'{target_job_id}: {e}'
            raise LavaError(return_info['error'], data=return_info)

    return return_info
