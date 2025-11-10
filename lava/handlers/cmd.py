"""
Run a single command.

Payload is the command string.

"""

from __future__ import annotations

import logging
import os
import shlex
import subprocess
import sys
from tempfile import NamedTemporaryFile, mkdtemp
from typing import Any

import boto3
import jinja2

from lava.config import LOGNAME, STATUS_TIMEOUT, config
from lava.lavacore import DEFER_ON_EXIT, LavaError, jinja_render_vars, job_environment
from lava.lib.aws import s3_split, s3_upload
from lava.lib.datetime import duration_to_seconds
from lava.lib.fileops import read_head_or_tail
from lava.lib.misc import dict_check, str2bool
from lava.lib.process import runpg

__author__ = 'Murray Andrews'

LOG = logging.getLogger(name=LOGNAME)

JOB_PARAMS_REQUIRED_FIELDS = set()
JOB_PARAMS_OPTIONAL_FIELDS = {'args', 'env', 'jinja', 'timeout', 'vars'}


# ------------------------------------------------------------------------------
def run(
    job_spec: dict[str, Any],
    realm_info: dict[str, Any],
    tmpdir: str,
    s3tmp: str,
    dev_mode: bool = False,
    aws_session: boto3.Session = None,
) -> dict[str, Any]:
    """
    Run single command.

    The output is dropped in the s3tmp area unless dev_mode is enabled, in which
    case it is emitted locally.

    Allowed job parameters are:

    - args
        A list of zero or more arguments. Optional.

    - env
        A map of environment variables.

    - jinja
        An optional boolean indicating whether Jinja rendering is enabled.
        Default True.

    - timeout
        Run timeout for the executable. Its a really bad idea to make this
        longer than the visibility period on the worker queue.

    - vars
        An optional dictionary of variables to use when Jinja rendering the
        payload.

    :param job_spec:        The job spec from the DynamoDB database.
    :param realm_info:      Realm specific parameters.
    :param tmpdir:          A local temporary directory.
    :param s3tmp:           A prefix in S3 where temporary assets can be created
                            and left for others to pick up for limited time.
    :param dev_mode:        If True, emit stdout / stderr locally instead of
                            copying to S3. Default False.
    :param aws_session:     A boto3 Session()

    :return:                A dictionary of parameters that are available to
                            on-success, on-error, on-retry handlers.
    """

    if not aws_session:
        aws_session = boto3.Session()

    if not job_spec['payload']:
        raise LavaError('payload required')

    parameters = job_spec.get('parameters', {})
    try:
        dict_check(
            parameters, required=JOB_PARAMS_REQUIRED_FIELDS, optional=JOB_PARAMS_OPTIONAL_FIELDS
        )
    except ValueError as e:
        raise LavaError(f'Bad job parameters: {e}')

    # ----------------------------------------
    # Prepare for Jinja rendering

    job_vars = parameters.get('vars', {})
    if not isinstance(job_vars, dict):
        raise LavaError('vars must be a map/dict')
    enable_jinja = parameters.get('jinja', True)
    render_vars = jinja_render_vars(job_spec, realm_info, vars=job_vars)

    # ----------------------------------------
    # Prepare command args

    try:
        command = shlex.split(job_spec['payload']) + [str(a) for a in parameters.get('args', [])]

        # Render the args
        if enable_jinja:
            command = [jinja2.Template(a).render(**render_vars) for a in command]
    except Exception as e:
        raise LavaError(f'Bad payload: {e}')

    LOG.debug('Command : %s', command)

    # ----------------------------------------
    # Prepare the environment

    env = job_environment(
        job_spec,
        realm_info,
        base=dict(os.environ),
        render_vars=render_vars if enable_jinja else None,
        LAVA_S3_TMP=s3tmp,
    )
    if config('JOB_LOCAL_TMPDIR', str2bool):
        env['TMPDIR'] = mkdtemp(prefix='.lava.', suffix='.tmp', dir=tmpdir)
    # LOG.debug('Command environment: %s', env)  # noqa: ERA001

    # ----------------------------------------
    # Run the command and capture output.

    return_info = {'exit_status': 0, 'output': []}
    failed = False
    fail_reason = None
    job_result = {'payload': job_spec['payload']}

    try:
        with (
            NamedTemporaryFile(dir=tmpdir, delete=False, suffix='.stdout') as stdout,
            NamedTemporaryFile(dir=tmpdir, delete=False, suffix='.stderr') as stderr,
        ):
            runpg(
                command,
                check=True,
                stdin=subprocess.DEVNULL,
                stdout=sys.stdout if dev_mode else stdout,
                stderr=sys.stderr if dev_mode else stderr,
                timeout=duration_to_seconds(parameters.get('timeout', config('CMD_TIMEOUT'))),
                shell=False,
                text=False,
                cwd=tmpdir,
                env=env,
                start_new_session=True,
                kill_event=DEFER_ON_EXIT,
            )
            job_result['exit_status'] = 0

    except subprocess.TimeoutExpired as e:
        failed = True
        fail_reason = f'Timed out after {e.timeout} seconds'
        return_info['exit_status'] = STATUS_TIMEOUT
        job_result['exit_status'] = STATUS_TIMEOUT

    except subprocess.CalledProcessError as e:
        failed = True
        fail_reason = f'Failed with exit status {e.returncode}'
        return_info['exit_status'] = e.returncode
        job_result['exit_status'] = e.returncode
        try:
            return_info['error'] = read_head_or_tail(
                stderr.name, config('STDERR_SIZE', int)
            ).strip()
            # DynamoDB didn't use to be able to handle empty strings.
            if not return_info['error']:
                # noinspection PyTypedDict
                return_info['error'] = None
        except FileNotFoundError:
            return_info['error'] = f'Cannot read {stderr.name}'
            LOG.critical(
                return_info['error'],
                extra={
                    'event_type': 'job',
                    'job_id': job_spec['job_id'],
                    'run_id': job_spec['run_id'],
                },
            )

    # ----------------------------------------
    # Success or fail, copy any output to S3. Note that the result info
    # is passed as data to the exception on failure.

    s3 = aws_session.client('s3')
    s3bucket, s3prefix = s3_split(s3tmp)
    for title, fname in ('stdout', stdout.name), ('stderr', stderr.name):
        s3key = f'{s3prefix}/{title}'
        if os.path.getsize(fname) > 0:
            s3_upload(s3bucket, s3key, fname, s3, kms_key=realm_info.get('s3_key'))
            job_result[title] = f's3://{s3bucket}/{s3key}'
            LOG.debug('Uploaded %s to %s', fname, job_result[title])

    return_info['output'].append(job_result)

    if failed:
        raise LavaError(fail_reason, data=return_info)

    return return_info
