"""Get a file from a SMB file share."""

from __future__ import annotations

import logging
import os.path
import subprocess
import sys
from typing import Any

import boto3
import jinja2

from lava.config import LOGNAME, STATUS_TIMEOUT, config
from lava.lavacore import DEFER_ON_EXIT, LavaError, jinja_render_vars
from lava.lib.aws import s3_split, s3_upload
from lava.lib.datetime import duration_to_seconds
from lava.lib.fileops import read_head_or_tail
from lava.lib.misc import dict_check
from lava.lib.process import runpg
from lava.lib.smb import SMB_CLI, SMB_JOB_PARAMS_OPTIONAL_FIELDS, SMB_JOB_PARAMS_REQUIRED_FIELDS

__author__ = 'Murray Andrews, Alex Boul'

LOG = logging.getLogger(name=LOGNAME)

JOB_PARAMS_REQUIRED_FIELDS = SMB_JOB_PARAMS_REQUIRED_FIELDS
JOB_PARAMS_OPTIONAL_FIELDS = SMB_JOB_PARAMS_OPTIONAL_FIELDS & {'kms_key_id'}


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
    Get a file from a SMB file share.

    Allowed job parameters are (* means optional):

    - conn_id
        A connection ID for the source SMB server.

    - share_name
        The name of the file share for the path.

    - path
        Source path within the remote file share. This will be jinja rendered.

    - file
        Source file. If it starts with `s3://` it is assumed to be an object in
        S3, otherwise a local file. If local and not an absolute path, it will
        be treated as relative to the basedir parameter. This will be jinja
        rendered. This will be jinja rendered.

    - basedir*
        If the target file is specified as a relative filename, it will be
        treated as relative to the specified directory. Defaults to the lava
        temporary directory for the job.

    - kms_key_id*
        AWS KMS key to use for uploading data to S3.

    - jinja*
        An optional boolean indicating whether Jinja rendering is enabled for
        the target path. Default True.

    - timeout*
        Run timeout for each payload element. Its a really bad idea to make this
        longer than the visibility period on the worker queue. Default is 10m.

    - vars*
        An optional dictionary of variables to use when Jinja rendering.

    The payload is ignored.

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

    parameters = job_spec.get('parameters', {})
    try:
        dict_check(
            parameters, required=JOB_PARAMS_REQUIRED_FIELDS, optional=JOB_PARAMS_OPTIONAL_FIELDS
        )
    except ValueError as e:
        raise LavaError(f'Bad job parameters: {e}')

    timeout = duration_to_seconds(parameters.get('timeout', config('SMB_TIMEOUT')))

    basedir = parameters.get('basedir', tmpdir)

    # ----------------------------------------
    # Jinja rendering

    path = parameters['path']
    dst_file = parameters['file']  # type: str

    if parameters.get('jinja', True):
        job_vars = parameters.get('vars', {})
        if not isinstance(job_vars, dict):
            raise LavaError('vars must be a map/dict')
        render_vars = jinja_render_vars(job_spec, realm_info, vars=job_vars)

        path = jinja2.Template(path).render(**render_vars)
        dst_file = jinja2.Template(dst_file).render(**render_vars)

    # If file is relative, add the base dir.
    if not dst_file.startswith('s3://') and not os.path.isabs(dst_file):
        if not os.path.isabs(basedir):
            basedir = os.path.abspath(basedir)

        dst_file = os.path.join(basedir, dst_file)

    # ----------------------------------------
    # Get file using Lava SMB CLI

    conn_id = parameters['conn_id']
    return_info = {'exit_status': 0, 'output': []}

    # ----------------------------------------
    # Build the CLI command to get file from SMB

    cli_cmd = [
        SMB_CLI,
        '--profile',
        aws_session.profile_name,
        '--realm',
        realm_info['realm'],
        '--conn-id',
        conn_id,
        '--tag',
        f'{job_spec["job_id"]}:{job_spec["run_id"]}',
        'get',
        f'{parameters["share_name"]}:{path}',
        dst_file,
    ]

    if parameters.get('kms_key_id', False):
        cli_cmd.append('--kms-key-id')
        cli_cmd.append(parameters['kms_key_id'])

    stdout_file = os.path.join(tmpdir, 'stdout')
    stderr_file = os.path.join(tmpdir, 'stderr')

    LOG.debug('CLI cmd: %s', cli_cmd)

    failed = False
    fail_reason = None
    return_info = {'exit_status': 0, 'output': []}
    job_result = {'exit_status': 0}

    try:
        with open(stdout_file, 'w') as stdout, open(stderr_file, 'w') as stderr:
            runpg(
                cli_cmd,
                check=True,
                stdin=subprocess.DEVNULL,
                stdout=sys.stdout if dev_mode else stdout,
                stderr=sys.stderr if dev_mode else stderr,
                timeout=timeout,
                shell=False,
                text=False,
                cwd=tmpdir,
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
                stderr_file, config('STDERR_SIZE', int)
            ).strip()
            # DynamoDB didn't use to be able to handle empty strings.
            if not return_info['error']:
                return_info['error'] = None
        except FileNotFoundError:
            return_info['error'] = f'Cannot read {stderr_file}'
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
    for title, fname in ('stdout', stdout_file), ('stderr', stderr_file):
        if os.path.getsize(fname) > 0:
            s3_upload(
                bucket=s3bucket,
                key=s3prefix + '/' + os.path.basename(fname),
                filename=fname,
                s3_client=s3,
                kms_key=realm_info.get('s3_key'),
            )
            job_result[title] = f's3://{s3bucket}/{s3prefix}/{os.path.basename(fname)}'

    return_info['output'].append(job_result)

    if failed:
        raise LavaError(fail_reason, data=return_info)

    # ----------------------------------------
    return {
        'exit_status': 0,
        'source': f'{parameters["share_name"]}:{path}',
        'destination': dst_file,
    }
