"""
Run a directed acyclic graph of jobs.

They all run under the same run ID.

The payload is a map. The keys are the IDs of the jobs to run and the values are
the list of IDs for jobs on which the key job is dependent.

Every job that occurs in either a key or a value is run. The map is only there
to specify dependencies. If a dependency has an empty (or null) key, the dependent
jobs are run but they may not need to be an predecessor of any other job.

"""

from __future__ import annotations

import concurrent.futures
import logging
from fnmatch import fnmatchcase
from graphlib import CycleError, TopologicalSorter  # noqa: I201
from pathlib import Path  # noqa: I100, I201
from threading import current_thread
from typing import Any

import boto3
from dateutil.tz import UTC

from lava.config import LOGNAME, config
from lava.lava import run_job
from lava.lavacore import LavaError, get_job_spec
from lava.lib.misc import dict_check

__author__ = 'Murray Andrews'

LOG = logging.getLogger(name=LOGNAME)

JOB_PARAMS_REQUIRED_FIELDS = {}
JOB_PARAMS_OPTIONAL_FIELDS = {
    'job_prefix',
    'workers',
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
    Dispatch a directed acyclic graph of jobs.

    The payload is a map. The keys are the IDs of the jobs to run and the values
    are the list of IDs for jobs on which the key job is dependent. All jobs
    share the same job run ID and hence the same temp dir.

    While explicit dependencies are honoured, there is no guarantee that the
    jobs will execute in the same order each time.

    Allowed job parameters are:

    - job_prefix:
        Prepend the specified value to each job_id in the payload.

    - workers:
        Number of worker threads for running dag component jobs. This is not
        related to the number of lava worker threads. Defaults to CPU count.

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

    if not isinstance(job_spec['payload'], dict):
        raise LavaError('payload must be a map')

    profile_name = aws_session.profile_name
    parameters = job_spec.get('parameters', {})

    try:
        dict_check(
            parameters, required=JOB_PARAMS_REQUIRED_FIELDS, optional=JOB_PARAMS_OPTIONAL_FIELDS
        )
    except ValueError as e:
        raise LavaError(f'Bad job parameters: {e}')

    workers = int(parameters.get('workers', config('DAG_WORKERS', int)))
    max_workers = config('DAG_MAX_WORKERS', int)
    if workers > max_workers:
        LOG.warning(
            f'Too many DAG workers ({workers}): limiting to {max_workers}',
            extra={'event_type': 'job', 'job_id': job_spec['job_id'], 'run_id': job_spec['run_id']},
        )
        workers = max_workers

    # Normalise the job dag
    job_prefix = parameters.get('job_prefix', '')
    payload = {
        f'{job_prefix}{job}': (
            []
            if not dep
            else (
                [f'{job_prefix}{dep}']
                if isinstance(dep, str)
                else [f'{job_prefix}{d}' for d in dep]
            )
        )
        for job, dep in job_spec['payload'].items()
    }
    LOG.debug('Normalised payload: %s', payload)

    job_dag = TopologicalSorter(graph=payload)
    try:
        job_dag.prepare()
    except CycleError as e:
        raise LavaError(f'Jobs are in a cycle: {", ".join(e.args[1])}')

    # ----------------------------------------
    # Get the DynamoDB job table

    job_table_name = 'lava.' + job_spec['realm'] + '.jobs'
    try:
        job_table = aws_session.resource('dynamodb').Table(job_table_name)
    except Exception as e:
        raise Exception(f'Cannot get DynamoDB table {job_table_name} - {e}')

    # ----------------------------------------
    # Loop through the jobs in the dag

    return_info = {'exit_status': 0, 'jobs': [], 'failed_jobs': []}
    can_fail_patterns = parameters.get('can_fail', [])
    if isinstance(can_fail_patterns, str):
        can_fail_patterns = [can_fail_patterns]

    with concurrent.futures.ThreadPoolExecutor(
        max_workers=workers, thread_name_prefix=current_thread().name
    ) as executor:
        while job_dag.is_active():
            ready_to_run = job_dag.get_ready()
            LOG.info(
                f'Ready to run: {", ".join(ready_to_run)}',
                extra={
                    'event_type': 'job',
                    'job_id': job_spec['job_id'],
                    'run_id': job_spec['run_id'],
                },
            )

            # --------------------------------
            # Job initiation phase

            futures = {}

            for child_job_id in ready_to_run:
                try:
                    child_job_spec = prepare_child_job(
                        child_job_id=child_job_id, parent_job_spec=job_spec, job_table=job_table
                    )
                except Exception as e:
                    return_info['exit_status'] = 1
                    return_info['error'] = f'Job {child_job_id} failed: {e}'
                    raise LavaError(f'{child_job_id}: {e}', data=realm_info)

                # Kick off the child jobs
                LOG.info(
                    f'Submitting child job {child_job_id} to executor',
                    extra={
                        'event_type': 'job',
                        'job_id': job_spec['job_id'],
                        'run_id': job_spec['run_id'],
                    },
                )
                futures[
                    executor.submit(
                        run_child_job, child_job_spec, realm_info, tmpdir, dev_mode, profile_name
                    )
                ] = child_job_id

            # --------------------------------
            # Job rendevouz and completion phase

            for future in concurrent.futures.as_completed(futures):
                child_job_id = futures[future]
                LOG.debug(f'Harvesting {child_job_id}')
                job_dag.done(child_job_id)

                try:
                    _ = future.result()
                except Exception as e:
                    return_info['failed_jobs'].append(child_job_id)
                    if any(fnmatchcase(child_job_id, glob) for glob in can_fail_patterns):
                        continue
                    return_info['exit_status'] = 1
                    return_info['error'] = f'Job {child_job_id}: {e}'
                    raise LavaError(return_info['error'], data=return_info)
                else:
                    LOG.info(
                        f'Job {child_job_id} done',
                        extra={
                            'event_type': 'job',
                            'job_id': job_spec['job_id'],
                            'run_id': job_spec['run_id'],
                        },
                    )
                    return_info['jobs'].append(child_job_id)

    return return_info


# ------------------------------------------------------------------------------
def prepare_child_job(
    child_job_id: str, parent_job_spec: dict[str, Any], job_table
) -> dict[str, Any]:
    """
    Prepare the child job spec.

    :param child_job_id:        The child job ID.
    :param parent_job_spec:     The parent job spec.
    :param job_table:           boto3 resource for the DynamoDB jobs table.

    :return:                    The prepared child job spec.

    """

    child_job_spec = get_job_spec(child_job_id, job_table)

    # Make sure the worker name matches
    if child_job_spec['worker'] != parent_job_spec['worker']:
        raise LavaError(
            f'Worker mismatch: Expected {parent_job_spec["worker"]}'
            f' but got {child_job_spec["worker"]}'
        )

    # Augment the child job spec. Same run_id as the parent job.
    child_job_spec['run_id'] = parent_job_spec['run_id']
    child_job_spec['ts_dispatch'] = parent_job_spec['ts_dispatch']
    child_job_spec['realm'] = parent_job_spec['realm']

    # Configure globals for the child. We distinguish between the master job
    # which is at the top of the tree and the parent job which is the
    # immediate parent. In most cases they will be the same. master_* vars
    # are already set at this point

    child_job_spec['globals'].update(parent_job_spec['globals'])  # type: dict
    lava_globals = child_job_spec['globals'].setdefault('lava', {})

    lava_globals['parent_job_id'] = parent_job_spec['job_id']
    lava_globals['parent_start'] = parent_job_spec['ts_start']
    lava_globals['parent_ustart'] = parent_job_spec['ts_start'].astimezone(UTC)

    LOG.debug(f'Child job {child_job_id} in dag is {child_job_spec}')

    return child_job_spec


# ------------------------------------------------------------------------------
def run_child_job(
    child_job_spec: dict[str, Any],
    realm_info: dict[str, Any],
    tmpdir: str | Path,
    dev_mode: bool,
    profile_name: str,
) -> dict[str, Any]:
    """
    Run the child job in a separate thread.

    :param child_job_spec:  Child job spec.
    :param realm_info:      The realm info.
    :param tmpdir:          Temp directory.
    :param dev_mode:        Passed to the job handler. Its up to the handler to
                            decide what it does with this. Default False.
    :param profile_name:    Boto3 profile name.

    :return:                Whatever the job returns.
    """

    # Need a new boto3 session for this thread
    aws_session = boto3.Session(profile_name=profile_name)

    return run_job(
        child_job_spec,
        realm_info,
        tmpdir=tmpdir,  # Children share the same working dir
        cleanup=False,
        dev_mode=dev_mode,
        aws_session=aws_session,
    )
