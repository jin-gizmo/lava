"""
Lava provided external client SQL handler.

This is essentially a hybrid of sqlc and sql job types. Unlike sqlc, it uses
a common lava CLI database client instead of using a native CLI client.

"""

from __future__ import annotations

import logging
import os
import subprocess
import sys
from contextlib import suppress
from typing import Any

import boto3
import jinja2

from lava.config import LOGNAME, STATUS_TIMEOUT, config
from lava.lava import get_payload_from_s3
from lava.lavacore import DEFER_ON_EXIT, LavaError, jinja_render_vars, job_environment
from lava.lib.aws import s3_split, s3_upload
from lava.lib.datetime import duration_to_seconds
from lava.lib.fileops import read_head_or_tail
from lava.lib.misc import dict_check, str2bool
from lava.lib.process import runpg

__author__ = 'Murray Andrews'

LOG = logging.getLogger(name=LOGNAME)

JOB_PARAMS_REQUIRED_FIELDS = {'conn_id'}
JOB_PARAMS_OPTIONAL_FIELDS = {
    'batch_size',
    'delimiter',
    'dialect',
    'doublequote',
    'escapechar',
    'format',
    'header',
    'jinja',
    'level',
    'quotechar',
    'quoting',
    'raw',
    'timeout',
    'transaction',
    'vars',
}

SQLV_CLI = 'lava-sql'


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
    Run an SQL payload using the lava-sql utility.

    The output is dropped in the s3tmp area.

    Allowed job parameters are (* means mandatory):

    - batch_size
        Number of rows to fetch at a time.

    - conn_id *
        A connectiion ID for the target DB.

    - format
        Output format -- Whatever is supported by lava-sql.

    - transaction
        If True, the sequence of SQLs is run within a transaction.
        Default False.

    - jinja
        An optional boolean indicating whether Jinja rendering is enabled.
        Default True.

    - header
        If True, add a header for SELECT outputs.

    - level
        Debugging level for the lava-sql utility.

    - raw
        By default, an attempt will be made to split each payload file into
        individual SQL statements. This should be safe in most cases. To
        suppress this behaviour and run the payload as-is, set raw to True.

    - timeout
        Run timeout for each payload element. Its a really bad idea to make this
        longer than the visibility period on the worker queue.

    - vars
        An optional dictionary of variables to use when Jinja rendering the SQL.

    Optional CSV formatting parameters:

    - delimiter
        Field delimiter. Default '|'

    - dialect
        As for csv.writer. Default excel.

    - doublequote
        As for csv.writer. Default False.

    - escapechar
        As for csv.writer. Default None.

    - quotechar
        As for csv.writer. Default '"'.

    - quoting
        As for csv.writer ``QUOTE_`` parameters (without the ``QUOTE_`` prefix).
        Default "minimal" (QUOTE_MINIMAL).

    :param job_spec:        The job spec from the DynamoDB database.
    :param realm_info:      Realm specific parameters.
    :param tmpdir:          A local temporary directory.
    :param s3tmp:           A prefix in S3 where temporary assets can be created
                            and left for others to pick up for limited time.
    :param dev_mode:        If True, emit stdout/stderr locally instead of
                            sending to S3. Default False.
    :param aws_session:     A boto3 Session()

    :return:                A dictionary of parameters that are available to
                            on-success, on-error, on-retry handlers.

    """
    parameters = job_spec['parameters']

    try:
        dict_check(
            parameters, required=JOB_PARAMS_REQUIRED_FIELDS, optional=JOB_PARAMS_OPTIONAL_FIELDS
        )
    except ValueError as e:
        raise LavaError(f'Bad job parameters: {e}')

    timeout = duration_to_seconds(parameters.get('timeout', config('SQLV_TIMEOUT')))

    job_vars = parameters.get('vars', {})
    if not isinstance(job_vars, dict):
        raise LavaError('vars must be a map/dict')
    enable_jinja = parameters.get('jinja', True)
    render_vars = jinja_render_vars(job_spec, realm_info, vars=job_vars)

    if not aws_session:
        aws_session = boto3.Session()

    conn_id = parameters['conn_id']

    return_info = {'exit_status': 0, 'output': []}

    # ----------------------------------------
    # Build the CLI command

    cli_cmd = [
        SQLV_CLI,
        '--profile',
        aws_session.profile_name,
        '--realm',
        realm_info['realm'],
        '--conn-id',
        conn_id,
        '--tag',
        f'{job_spec["job_id"]}:{job_spec["run_id"]}',
        '--batch-size',
        str(parameters.get('batch_size', config('SQL_BATCH_SIZE', int))),
    ]

    # Params that take a simple argument
    for param in 'format', 'level':
        with suppress(KeyError):
            cli_cmd.extend([f'--{param}', parameters[param]])

    if parameters.get('header', False):
        cli_cmd.append('--header')

    # Add the boolean options that don't have a config() default
    for param in 'raw', 'transaction':
        if parameters.get(param, False):
            cli_cmd.append(f'--{param}')

    if parameters.get('format', 'csv') == 'csv':
        if parameters.get('doublequote', config('SQL_DOUBLEQUOTE', str2bool)):
            cli_cmd.append('--doublequote')
        # Add the string value based options that have a config default
        for param in 'delimiter', 'dialect', 'escapechar', 'quotechar', 'quoting':
            if (value := parameters.get(param, config('SQL_' + param.upper()))) is not None:
                cli_cmd.extend([f'--{param}', value])

    # ----------------------------------------
    # Prepare the environment

    env = job_environment(
        job_spec,
        realm_info,
        base=dict(os.environ),
        render_vars=render_vars if enable_jinja else None,
    )
    # LOG.debug('Command environment: %s', env)  # noqa: ERA001

    # ----------------------------------------
    # Download each payload item and run the SQL

    for payload_file in get_payload_from_s3(
        payload=job_spec['payload'],
        realm_info=realm_info,
        local_dir=tmpdir,
        max_size=config('SQL_MAX_PAYLOAD_SIZE'),
        aws_session=aws_session,
    ):
        cli_cmd.append(payload_file)
        base = os.path.basename(payload_file)

        # ------------------------------------
        # Render the file using Jinja
        if enable_jinja:
            try:
                src_dir = os.path.dirname(payload_file)
                template_loader = jinja2.FileSystemLoader(searchpath=src_dir)
                template_env = jinja2.Environment(
                    loader=template_loader, autoescape=jinja2.select_autoescape()
                )
                template = template_env.get_template(base)
                with open(payload_file, 'w') as ofp:
                    ofp.write(template.render(**render_vars))
            except Exception as e:
                return_info['exit_status'] = 1
                return_info['error'] = f'Jinja2 render failed on {base}: {e}'
                raise LavaError(
                    f'Failed with exit status {return_info["exit_status"]}', data=return_info
                )

    stdout_file = os.path.join(tmpdir, 'stdout')
    stderr_file = os.path.join(tmpdir, 'stderr')

    # We can't rely on stdout for binary output as colorama and God knows what
    # else wants to mess with stdout before passing it to lava-sql.
    cli_cmd.extend(['--output', stdout_file])

    LOG.debug('CLI cmd: %s', cli_cmd)

    failed = False
    fail_reason = None
    job_result = {'exit_status': 0}

    try:
        with open(stdout_file, 'wb') as stdout, open(stderr_file, 'w') as stderr:
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
                stderr_file, config('STDERR_SIZE', int)
            ).strip()
            # DynamoDB didn't use to be able to handle empty strings.
            if not return_info['error']:
                return_info['error'] = None  # noqa
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

    return return_info
