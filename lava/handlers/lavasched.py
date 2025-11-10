"""Lava internal handler to build the dispatcher cron schedule."""

from __future__ import annotations

import logging
import os
import subprocess
from collections.abc import Iterable, Iterator
from difflib import unified_diff
from filecmp import cmp
from shlex import quote
from typing import Any

import boto3

from lava.config import LOGNAME, config
from lava.lavacore import JobSchedule, LavaError
from lava.lib.aws import dynamo_unmarshall_item, s3_split, s3_upload
from lava.lib.misc import dict_check, listify

__author__ = 'Murray Andrews'

LOG = logging.getLogger(name=LOGNAME)

CRONTAB_MARKER_START = '#### Lava Schedules Start ####'
CRONTAB_MARKER_END = '#### Lava Schedules End ####'

JOB_SPEC_REQUIRED_FIELDS = {'job_id', 'worker'}

JOB_PARAMS_REQUIRED_FIELDS = {'dispatcher'}
JOB_PARAMS_OPTIONAL_FIELDS = {'args', 'env'}


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
    Build the crontab for the dispatcher.

    The payload is ignored.

    Allowed job parameters are:

    - dispatcher
        Name of dispatcher, or a list of names, specifying for which dispatchers
        schedules should be built.

    - args
        A list of zero or more additional arguments for the dispatch. Optional.

    - env
        A dictionary of environment variables that will be placed in the
        crontab. The most useful values are ``CRON_TZ`` and ``TZ`` that control
        the timezone used by the cron scheduler and the timezone used by the
        jobs respectively.

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

    return_info: dict[str, Any] = {'exit_status': 0}

    try:
        dict_check(job_spec['parameters'], required=JOB_PARAMS_REQUIRED_FIELDS)
    except ValueError as e:
        raise LavaError(f'Bad job parameters: {e}')

    parameters = job_spec['parameters']

    try:
        dict_check(
            parameters, required=JOB_PARAMS_REQUIRED_FIELDS, optional=JOB_PARAMS_OPTIONAL_FIELDS
        )
    except ValueError as e:
        raise LavaError(f'Bad job parameters: {e}')

    if not aws_session:
        aws_session = boto3.Session()

    old_cron = os.path.join(tmpdir, 'crontab.old')
    new_cron = os.path.join(tmpdir, 'crontab.new')

    get_crontab(old_cron)

    # ----------------------------------------
    # Create a new crontab

    jobs_table_name = f'lava.{job_spec["realm"]}.jobs'

    # Read the old crontab to find where we insert our stuff
    start_marker_found = False
    end_marker_found = False

    with open(old_cron) as old_fp, open(new_cron, 'w') as new_fp:
        # Read the old one up to the start marker. Preamble lines are copied as is to new cron.
        for line in old_fp:
            line = line.rstrip('\n')
            if line == CRONTAB_MARKER_START:
                start_marker_found = True
                break
            print(line, file=new_fp)

        # Found the start marker or there wasn't one.
        print(CRONTAB_MARKER_START, file=new_fp)

        # Add environment variables.
        env = parameters.get('env', {})
        env['LAVA_REALM'] = job_spec['realm']
        for k, v in sorted(env.items()):
            print(f'{k}={v}', file=new_fp)

        # Get jobs from jobs table and extrude the new cron entries
        for d in sorted(listify(parameters['dispatcher'])):
            for job_item in get_scheduled_jobs(jobs_table_name, d, aws_session=aws_session):
                try:
                    for cron_item in generate_crontab_entries(
                        job_item['schedule'],
                        config('DISPATCHER'),
                        '--worker',
                        job_item['worker'],
                        *parameters.get('args', []),
                        job_item['job_id'],
                    ):
                        print(cron_item, file=new_fp)
                except LavaError as e:
                    raise LavaError(f'Job {job_item["job_id"]}: {e}')

        print(CRONTAB_MARKER_END, file=new_fp)

        # Skip forward through the old file to find the end marker
        if start_marker_found:
            # We found a start marker so look for end marker
            for line in old_fp:
                line = line.rstrip('\n')
                if line == CRONTAB_MARKER_END:
                    end_marker_found = True
                    break

        # Copy the rest of the old file
        if end_marker_found:
            for line in old_fp:
                line = line.rstrip('\n')
                print(line, file=new_fp)

    LOG.debug('New crontab built')

    # ----------------------------------------
    # Check if the new crontab is different from previous
    if cmp(old_cron, new_cron, shallow=False):
        LOG.debug('Old and new crontabs are the same - nothing to do')
        return return_info

    # New crontab is different. Need to install. Copy old and new crontab to S3.
    s3 = aws_session.client('s3')
    bucket, prefix = s3_split(s3tmp)
    s3_key_new_cron = f'{prefix}/crontab.new'

    # Preserve the old crontab just in case.
    if os.path.getsize(old_cron) > 0:
        s3_key_old_cron = f'{prefix}/crontab.old'
        try:
            s3_upload(
                bucket=bucket,
                key=s3_key_old_cron,
                filename=old_cron,
                s3_client=s3,
                kms_key=realm_info.get('s3_key'),
            )
        except Exception as e:
            return_info['exit_status'] = 2
            raise LavaError(f'Could not copy old crontab to S3 - {e}', data=return_info)
        return_info['crontab.old'] = f's3://{bucket}/{s3_key_old_cron}'

    # Keep a copy of the new crontab in S3
    s3_upload(
        bucket=bucket,
        key=s3_key_new_cron,
        filename=new_cron,
        s3_client=s3,
        kms_key=realm_info.get('s3_key'),
    )
    return_info['crontab.new'] = f's3://{bucket}/{s3_key_new_cron}'

    # ----------------------------------------
    # Calculate the differences between old and new. Helps schedule troubleshooting.
    with open(old_cron) as old_fp, open(new_cron) as new_fp:
        return_info['crontab.diff'] = list(
            unified_diff(
                old_fp.read().splitlines(),
                new_fp.read().splitlines(),
                fromfile='Old',
                tofile='New',
                n=1,
            )
        )

    # ----------------------------------------
    # Install the new crontab.
    try:
        put_crontab(new_cron)
    except Exception as e:
        raise LavaError(f'Could not install new crontab - {e}', data=return_info)

    return return_info


# ------------------------------------------------------------------------------
def get_crontab(filename: str) -> None:
    """Get the current crontab into the specified file."""

    LOG.debug('Getting old crontab')
    try:
        with open(filename, 'w') as fp:
            subprocess.run(
                ['crontab', '-l'],
                check=True,
                stdin=subprocess.DEVNULL,
                stdout=fp,
                stderr=subprocess.DEVNULL,
                shell=False,
            )
    except subprocess.CalledProcessError:
        # Assume there is no existing crontab.
        LOG.debug('No existing crontab')
        pass


# ------------------------------------------------------------------------------
def put_crontab(filename: str) -> None:
    """Update the crontab from the specified file."""

    LOG.debug('Installing new crontab')
    subprocess.run(
        ['crontab', filename],
        check=True,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        shell=False,
    )


# ------------------------------------------------------------------------------
def get_scheduled_jobs(
    jobs_table_name: str, dispatcher: str, aws_session: boto3.Session = None
) -> Iterable[dict[str, Any]]:
    """
    Get scheduled jobs for the specified dispatcher from the jobs table.

    :param jobs_table_name: Name of the lava jobs table.
    :param dispatcher:      Name of the dispatcher being scheduled.
    :param aws_session:     A boto3 session.
    :return:                An iterator of job specs containing a schedule.
    """

    dynamo = (aws_session or boto3.Session()).client('dynamodb')
    paginator = dynamo.get_paginator('query')

    response_iterator = paginator.paginate(
        TableName=jobs_table_name,
        IndexName='dispatcher-index',
        KeyConditionExpression='dispatcher = :dispatcher',
        ExpressionAttributeValues={':dispatcher': {'S': dispatcher}},
    )

    for response in response_iterator:
        for item in response['Items']:
            if not item.get('schedule'):
                continue

            try:
                dict_check(item, JOB_SPEC_REQUIRED_FIELDS)
            except ValueError as e:
                raise LavaError(f'Bad job record: {item} - {e}')

            # Convert the wacky DyanmoDB structure to something sane
            try:
                yield dynamo_unmarshall_item(item)
            except ValueError as e:
                raise LavaError(f'Cannot unmarshall DynamoDB entry: {item} - {e}')


# ------------------------------------------------------------------------------
def generate_crontab_entries(
    schedule: str | dict[str, Any] | list[str] | list[dict[str, Any]], *dispatcher_args: str
) -> Iterator[str]:
    """
    Generate crontab entries for the given job schedule to the specified file.

    :param schedule:    The schedule component of a job specification.
    :return:            An iterator of crontab entries.
    """

    # Can not use listify here -- it will shred dictionary schedule entries
    schedules = schedule if isinstance(schedule, list) else [schedule]
    for n, sched_spec in enumerate(schedules, 1):
        try:
            sched = JobSchedule(sched_spec)
        except LavaError as e:
            raise LavaError(f'Bad schedule entry {n}: {e}')

        if not sched.active:
            continue

        yield ' '.join((sched.crontab, *(quote(s) for s in dispatcher_args)))
