"""External client SQL handler."""

from __future__ import annotations

import logging
import os
import subprocess
import sys
from typing import Any

import boto3
import jinja2

from lava.config import LOGNAME, STATUS_TIMEOUT, config
from lava.connection import get_cli_connection
from lava.connection.core import make_application_name
from lava.lava import get_payload_from_s3
from lava.lavacore import DEFER_ON_EXIT, LavaError, jinja_render_vars
from lava.lib.aws import s3_split, s3_upload
from lava.lib.datetime import duration_to_seconds
from lava.lib.fileops import read_head_or_tail
from lava.lib.misc import dict_check
from lava.lib.process import runpg

__author__ = 'Murray Andrews'

LOG = logging.getLogger(name=LOGNAME)

JOB_PARAMS_REQUIRED_FIELDS = {'conn_id'}
JOB_PARAMS_OPTIONAL_FIELDS = {'args', 'jinja', 'timeout', 'vars'}


# ------------------------------------------------------------------------------
def run(
    job_spec: dict[str, Any],
    realm_info: dict[str, Any],
    tmpdir: str,
    s3tmp: str,
    dev_mode: bool = False,
    aws_session: boto3.Session = None,
) -> dict:
    """
    Run an SQL payload.

    The output is dropped in the s3tmp area.

    Allowed job parameters are (* means mandatory):

    - conn_id *
        A connectiion ID for the target DB.

    - args
        A list of zero or more additional arguments provided to the database
        client. Optional.

    - timeout
        Run timeout for each payload element. Its a really bad idea to make this
        longer than the visibility period on the worker queue.

    - jinja
        An optional boolean indicating whether Jinja rendering is enabled.
        Default True.

    - vars
        An optional dictionary of variables to use when Jinja rendering the SQL.

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

    args = [str(a) for a in parameters.get('args', [])]
    timeout = duration_to_seconds(parameters.get('timeout', config('SQLC_TIMEOUT')))
    conn_id = parameters['conn_id']
    env = {
        **os.environ,
        'LAVA_REALM': job_spec['realm'],
        # This helps for psql connections and does no harm for the others
        'PGAPPNAME': make_application_name(
            conn_id=conn_id, realm=job_spec['realm'], job_id=job_spec['job_id']
        ),
    }

    job_vars = parameters.get('vars', {})
    if not isinstance(job_vars, dict):
        raise LavaError('vars must be a map/dict')
    enable_jinja = parameters.get('jinja', True)
    render_vars = jinja_render_vars(job_spec, realm_info, vars=job_vars)

    if not aws_session:
        aws_session = boto3.Session()

    # ----------------------------------------
    # Get connection for the target DB. Using the CLI connector means
    # we get back a command to run.

    conn = get_cli_connection(conn_id, job_spec['realm'], workdir=tmpdir, aws_session=aws_session)
    LOG.debug('CONN %s', conn)

    return_info = {'exit_status': 0, 'output': []}

    # ----------------------------------------
    # Download each payload item and run the SQL

    for payload_file in get_payload_from_s3(
        payload=job_spec['payload'],
        realm_info=realm_info,
        local_dir=tmpdir,
        max_size=config('SQLC_MAX_PAYLOAD_SIZE'),
        aws_session=aws_session,
    ):
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

        stdout_file = os.path.join(tmpdir, base) + '.stdout'
        stderr_file = os.path.join(tmpdir, base) + '.stderr'

        failed = False
        fail_reason = None
        job_result = {'exit_status': 0, 'payload': base}

        try:
            with (
                open(stdout_file, 'w') as stdout,
                open(stderr_file, 'w') as stderr,
                open(payload_file) as stdin,
            ):
                runpg(
                    [conn, *args],
                    check=True,
                    stdin=stdin,
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
                    # noinspection PyTypedDict
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

    return return_info
