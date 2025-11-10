"""
Run a list of jobs.

They all run under the same run ID.

> Chain, chain, chain ... chain of jobs

The payload is either a comma separated list of job IDs or an actual list of
job IDs.

"""

from __future__ import annotations

import logging
from fnmatch import fnmatchcase
from typing import Any

import boto3
from dateutil.tz import UTC

from lava.config import LOGNAME
from lava.lava import run_job
from lava.lavacore import LavaError, get_job_spec
from lava.lib.misc import dict_check

__author__ = 'Murray Andrews'

LOG = logging.getLogger(name=LOGNAME)

JOB_PARAMS_REQUIRED_FIELDS = {}
JOB_PARAMS_OPTIONAL_FIELDS = {
    'job_prefix',
    'start',  # Start running at the first job with this job_id
    'can_fail',  # Jobs that are allowed to fail
}


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
    Dispatch a chain of jobs.

    The payload in this case is a list of job names either as a list or a comma
    separated string of job names. All jobs share the same job run ID and hence
    the same temp dir.

    Allowed job parameters are:

    - job_prefix:
        Prepend the specified value to each job_id in the payload.

    - start
        Job ID of the first job in the chain to run. This allows a chain to be
        run from somewhere other than the start of the chain.

    - can_fail
        A glob or list of globs for child job IDs that are permitted to fail
        without causing the chain job to fail.

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

    job_list = job_spec['payload']
    run_id = job_spec['run_id']

    # ----------------------------------------
    # Work out which job in the chain we should start with.

    if isinstance(job_list, str):
        job_list = [j.strip() for j in job_list.split(',')]
    elif not isinstance(job_list, list):
        raise LavaError('Bad payload: must be string or list')

    if job_prefix := parameters.get('job_prefix', ''):
        job_list = [f'{job_prefix}{job_id}' for job_id in job_list]

    if start_job := parameters.get('start'):
        # Find the start job
        if job_prefix:
            start_job = f'{job_prefix}{start_job}'
        try:
            job_list = job_list[job_list.index(start_job) :]
        except ValueError:
            raise LavaError(f'Requested start job {start_job} is not present in the chain')

    LOG.debug(f'Chain job list is {job_list}')

    if not job_list:
        raise LavaError('Job chain is empty')

    # ----------------------------------------
    # Get the DynamoDB job table

    job_table_name = 'lava.' + job_spec['realm'] + '.jobs'
    try:
        job_table = aws_session.resource('dynamodb').Table(job_table_name)
    except Exception as e:
        raise Exception(f'Cannot get DynamoDB table {job_table_name} - {e}')

    # ----------------------------------------
    # Loop through the jobs in the chain

    return_info = {'exit_status': 0, 'jobs': [], 'failed_jobs': []}

    ts_start = job_spec['ts_start']
    ts_ustart = job_spec['ts_start'].astimezone(UTC)
    can_fail_patterns = parameters.get('can_fail', [])
    if isinstance(can_fail_patterns, str):
        can_fail_patterns = [can_fail_patterns]

    for child_job_id in job_list:
        # ------------------------------------
        # Get the child job
        try:
            child_job_spec = get_job_spec(child_job_id, job_table)
        except LavaError as e:
            return_info['failed_jobs'].append(child_job_id)
            return_info['exit_status'] = 1
            return_info['error'] = f'Job {child_job_id} failed: {e}'
            raise LavaError(f'{child_job_id}: {e}', data=return_info)

        # ------------------------------------
        # Make sure the worker name matches
        if child_job_spec['worker'] != job_spec['worker']:
            return_info['failed_jobs'].append(child_job_id)
            return_info['exit_status'] = 1
            return_info['error'] = 'Job {}: Worker mismatch: Expected {} but got {}'.format(
                child_job_id, job_spec['worker'], child_job_spec['worker']
            )
            raise LavaError(return_info['error'], data=return_info)

        # ------------------------------------
        # Augment the child job spec. Same run_id as the parent job.
        child_job_spec['run_id'] = run_id
        child_job_spec['ts_dispatch'] = job_spec['ts_dispatch']
        child_job_spec['realm'] = job_spec['realm']

        # Configure globals for the child. We distinguish between the master job
        # which is at the top of the tree and the parent job which is the
        # immediate parent. In most cases they will be the same. master_* vars
        # are already set at this point

        child_job_spec['globals'].update(job_spec['globals'])  # type: dict
        lava_globals = child_job_spec['globals'].setdefault('lava', {})

        lava_globals['parent_job_id'] = job_spec['job_id']
        lava_globals['parent_start'] = ts_start
        lava_globals['parent_ustart'] = ts_ustart

        LOG.debug(f'Child job {child_job_id} in chain is {child_job_spec}')

        # ------------------------------------
        # Run the child job

        try:
            run_job(
                child_job_spec,
                realm_info,
                cleanup=False,
                tmpdir=tmpdir,  # Children share the same working dir
                dev_mode=dev_mode,
                aws_session=aws_session,
            )
            return_info['jobs'].append(child_job_id)
        except Exception as e:
            # Child jobs has failed -- we need to check if this child job is
            # allowed to fail.
            return_info['failed_jobs'].append(child_job_id)
            if any(fnmatchcase(child_job_id, glob) for glob in can_fail_patterns):
                continue
            return_info['exit_status'] = 1
            return_info['error'] = f'Job {child_job_id}: {e}'
            raise LavaError(return_info['error'], data=return_info)

    return return_info
