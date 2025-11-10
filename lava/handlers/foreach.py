"""
Run the same job multiple times with a sequence of different globals settings.

They all run under the same run ID.

> Super duper looper scooper.

The payload is a job ID.

"""

from __future__ import annotations

from copy import deepcopy
from itertools import islice
from typing import Any

import boto3
from dateutil.tz import UTC

from lava.config import LOG, config
from lava.foreach import Foreach
from lava.lava import run_job
from lava.lavacore import LavaError, get_job_spec, jinja_render_vars
from lava.lib.misc import dict_check

__author__ = 'Murray Andrews'

JOB_PARAMS_REQUIRED_FIELDS = {'foreach'}
JOB_PARAMS_OPTIONAL_FIELDS = {'can_fail', 'limit', 'jinja'}


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
    Dispatch the same job multiple times with a sequence of globals.

    The payload is a job ID. All jobs share the same job run ID.

    Required job parameters are:

    - foreach:
        A sequence generator for global values for each iteration.

    Allowed job parameters are:

    - can_fail
        A boolean that indicates if individual iterations are permitted to fail
        without causing the entire job to fail.

    - jinja
        Enable Jinja rendering. What gets rendered in the forach generator spec
        is controlled by the generator itself.

    - limit
        An integer. Attempting to run a foreach job with more than this many
        values will fail without any job being run at all. Defaults to the
        realm level value.

    :param job_spec:        The job spec from the DynamoDB database.
    :param realm_info:      Realm specific parameters.
    :param tmpdir:          A local temporary directory.
    :param s3tmp:           A prefix in S3 where temporary assets can be created
                            and left for others to pick up for limited time.
    :param dev_mode:        Not used for this handler itself but passed through
                            to jobs in the chain.
    :param aws_session:     A boto3 Session()

    :return:                A dictionary of parameters that are available to
                            on-success, on-error handlers.

    """

    if not aws_session:
        aws_session = boto3.Session()

    parameters = job_spec.get('parameters', {})

    try:
        dict_check(
            parameters, required=JOB_PARAMS_REQUIRED_FIELDS, optional=JOB_PARAMS_OPTIONAL_FIELDS
        )
    except ValueError as e:
        raise LavaError(f'Bad job parameters: {e}')

    fe_job_id = job_spec['payload']
    if not isinstance(fe_job_id, str):
        raise LavaError('Bad payload: must be string')
    run_id = job_spec['run_id']

    job_table_name = f'lava.{job_spec["realm"]}.jobs'
    try:
        job_table = aws_session.resource('dynamodb').Table(job_table_name)
    except Exception as e:
        raise LavaError(f'Cannot get DynamoDB table {job_table_name} - {e}')

    # Work out limits on how long our foreach is allowed to be
    fe_limit = int(parameters.get('limit', config('FOREACH_LIMIT', int)))
    if fe_limit > (fe_max_limit := config('FOREACH_MAX_LIMIT', int)):
        raise LavaError(f'foreach limit of {fe_limit} exceeds realm limit of {fe_max_limit}')
    LOG.debug('Limit=%d', fe_limit)

    # ----------------------------------------
    # Get the child job info

    try:
        fe_job_spec = get_job_spec(fe_job_id, job_table)
    except LavaError as e:
        return_info = {'exit_status': 1, 'error': f'Job {fe_job_id}: {e}'}
        raise LavaError(return_info['error'], data=return_info)

    # Make sure the worker name matches
    if fe_job_spec['worker'] != job_spec['worker']:
        raise LavaError(
            f'Job {fe_job_id}: Worker mismatch:'
            f' Expected {job_spec["worker"]} but got {fe_job_spec["worker"]}'
        )

    # ----------------------------------------
    # Get iteration value generator and make sure it's not too long.
    # The foreach handlers are iterators but here we want a strictly limited
    # sequence of values that must be no longer than the limit. To validate
    # this, we get limit+1 to check if limit has been exceeded.

    foreach_spec = parameters['foreach']
    jinja_enabled = parameters.get('jinja', True)
    with Foreach.handler(
        foreach_spec,
        job_id=job_spec['job_id'],
        realm=job_spec['realm'],
        render_vars=jinja_render_vars(job_spec, realm_info) if jinja_enabled else None,
        aws_session=aws_session,
    ) as fe:
        foreach_vals = tuple(islice(fe, fe_limit + 1))

    if len(foreach_vals) > fe_limit:
        return_info = {'exit_status': 1, 'error': f'foreach value list exceeds limit of {fe_limit}'}
        raise LavaError(return_info['error'], data=return_info)

    # ----------------------------------------
    # Prepare the child job for multiple runs.

    ts_start = job_spec['ts_start']
    ts_ustart = job_spec['ts_start'].astimezone(UTC)
    can_fail = parameters.get('can_fail', False)
    return_info = {
        'exit_status': 0,
        'limit': fe_limit,
        'foreach_len': len(foreach_vals),
        'jobs_completed': 0,
        'failed_indexes': [],
    }

    # Augment the child job spec. Same run_id as the parent job.
    fe_job_spec['run_id'] = run_id
    fe_job_spec['ts_dispatch'] = job_spec['ts_dispatch']
    fe_job_spec['realm'] = job_spec['realm']
    # Keep a pristine copy of our starting globals.
    fe_job_globals = {**fe_job_spec['globals'], **job_spec['globals']}

    # Configure globals for the child. We distinguish between the master job
    # which is at the top of the tree and the parent job which is the
    # immediate parent. In most cases they will be the same. master_* vars
    # are already set at this point
    lava_globals = fe_job_globals.setdefault('lava', {})
    lava_globals['parent_job_id'] = job_spec['job_id']
    lava_globals['parent_start'] = ts_start
    lava_globals['parent_ustart'] = ts_ustart

    # ----------------------------------------
    # Loop through the foreach values list

    for fe_index, fe_values in enumerate(foreach_vals[:fe_limit]):
        # Deep copy allows a fresh job spec to be passed into run_job() function preventing runtime
        # modifications (mainly Jinja rendering) from affecting subsequent runs of the child job
        fe_job_spec_copy = deepcopy(fe_job_spec)

        fe_job_spec_copy['globals'] = {**fe_job_globals, **fe_values}
        fe_job_spec_copy['globals']['lava']['foreach_index'] = fe_index

        LOG.debug('Foreach child job globals: %s', fe_job_spec_copy['globals'])

        # ------------------------------------
        # Run the child job

        try:
            run_job(
                fe_job_spec_copy,
                realm_info,
                cleanup=False,
                tmpdir=tmpdir,  # Children share the same working dir
                dev_mode=dev_mode,
                aws_session=aws_session,
            )
            return_info['jobs_completed'] += 1
        except Exception as e:
            return_info['failed_indexes'].append(fe_index)
            if can_fail:
                continue
            return_info['exit_status'] = 1
            return_info['error'] = f'Job {fe_job_id}: Index {fe_index}: {e}'
            raise LavaError(return_info['error'], data=return_info)

    return return_info
