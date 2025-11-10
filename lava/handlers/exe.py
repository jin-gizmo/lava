"""Download and run an executable."""

from __future__ import annotations

import logging
import os
import re
import shlex
import stat
import subprocess
import sys
from tempfile import mkdtemp
from typing import Any

import boto3
import jinja2

from lava.config import LAVA_CODE_DIR, LOGNAME, STATUS_TIMEOUT, config
from lava.connection import get_cli_connection
from lava.lava import get_payload_from_s3
from lava.lavacore import DEFER_ON_EXIT, LavaError, jinja_render_vars, job_environment
from lava.lib.aws import s3_split, s3_upload
from lava.lib.datetime import duration_to_seconds
from lava.lib.fileops import read_head_or_tail
from lava.lib.misc import dict_check, str2bool
from lava.lib.process import runpg

__author__ = 'Murray Andrews'

LOG = logging.getLogger(name=LOGNAME)

JOB_PARAMS_REQUIRED_FIELDS = set()
JOB_PARAMS_OPTIONAL_FIELDS = {'args', 'connections', 'env', 'jinja', 'timeout', 'vars'}


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
    Run standalone executables.

    The output is dropped in the s3tmp area. If multiple executables are run,
    the run is aborted if any of them fails.

    The payload is:

    ```bash
    s3-exe-location [args ...]
    ```

    Allowed job parameters are:

    - `args`:
        A list of zero or more additional arguments. Optional.

    - `connections`:
        A dictionary with keys that are connection labels and the values are
        conn_id. Optional.

    - `env`:
        A map of environment variables.

    - `timeout`:
        Run timeout for the executable. Its a really bad idea to make this
        longer than the visibility period on the worker queue.

    - `vars`:
        An optional dictionary of variables to use when Jinja rendering the
        args.

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

    # TODO: One day we could look at removing this restriction but its not
    #       straightforward due to the fact that the payload can include
    #       command line arguments and the stdout/stderr naming assumes uniqueness
    #       of the executable names. The latter could be fixed by modifying
    #       the names of these files (e.g. inserting a sequence number)
    #       but that has a backward compatibility impact. It could also
    #       lead to really messy job structures.
    if not isinstance(job_spec['payload'], str):
        raise LavaError('Only single string payloads are supported for exe jobs')

    if not aws_session:
        aws_session = boto3.Session()

    parameters = job_spec.get('parameters', {})

    try:
        dict_check(
            parameters, required=JOB_PARAMS_REQUIRED_FIELDS, optional=JOB_PARAMS_OPTIONAL_FIELDS
        )
    except ValueError as e:
        raise LavaError(f'Bad job parameters: {e}')

    timeout = duration_to_seconds(parameters.get('timeout', config('EXE_TIMEOUT')))

    # ----------------------------------------
    # Prepare for Jinja rendering

    job_vars = parameters.get('vars', {})
    if not isinstance(job_vars, dict):
        raise LavaError('vars must be a map/dict')
    enable_jinja = parameters.get('jinja', True)
    render_vars = jinja_render_vars(job_spec, realm_info, vars=job_vars)

    # ----------------------------------------
    # Prepare command args. All files get the same args.

    try:
        payload = shlex.split(job_spec['payload'])
    except Exception as e:
        raise LavaError(f'Bad payload: {e}')

    args = payload[1:] + [str(a) for a in parameters.get('args', [])]

    if enable_jinja:
        try:
            # Render the args
            args = [jinja2.Template(a).render(**render_vars) for a in args]
        except Exception as e:
            raise LavaError(f'Bad payload or args: {e}')

    LOG.debug('Command args: %s', args)

    # ----------------------------------------
    # Prepare the environment

    env = job_environment(
        job_spec,
        realm_info,
        base=dict(os.environ),
        render_vars=render_vars if enable_jinja else None,
        LAVA_S3_TMP=s3tmp,
        LAVA_S3_PAYLOAD=realm_info['s3_payloads'] + '/' + payload[0],
        # This helps Python exe's use the Lava libraries and connection manager
        PYTHONPATH=os.environ.get('PYTHONPATH', '') + ':' + LAVA_CODE_DIR,
    )
    if config('JOB_LOCAL_TMPDIR', str2bool):
        env['TMPDIR'] = mkdtemp(prefix='.lava.', suffix='.tmp', dir=tmpdir)
    # LOG.debug('Command environment: %s', env)  # noqa: ERA001

    # ----------------------------------------
    # See if we need to get connections.

    if not isinstance(parameters.get('connections', {}), dict):
        raise LavaError('connections parameter must be a map')

    for conn_label, conn_id in parameters.get('connections', {}).items():
        if not re.fullmatch(r'\w+', conn_label):
            raise LavaError(f'Bad connection label: {conn_label}')
        connector = get_cli_connection(
            conn_id, job_spec['realm'], workdir=tmpdir, aws_session=aws_session
        )
        LOG.debug('CONN %s', connector)
        env.update(
            {
                'LAVA_CONNID_' + conn_label.upper(): conn_id,
                'LAVA_CONN_' + conn_label.upper(): connector,
            }
        )

    return_info: dict[str, Any] = {'exit_status': 0, 'output': []}

    # ----------------------------------------
    # Retrieve the executable payload from S3 and make it executable.

    for payload_file in get_payload_from_s3(
        payload=payload[0],
        realm_info=realm_info,
        local_dir=tmpdir,
        max_size=config('EXE_MAX_PAYLOAD_SIZE'),
        aws_session=aws_session,
    ):
        os.chmod(payload_file, os.stat(payload_file).st_mode | stat.S_IXUSR)

        # ----------------------------------------
        # Run the command and capture output.

        base = os.path.basename(payload_file)
        stdout_file = os.path.join(tmpdir, base) + '.stdout'
        stderr_file = os.path.join(tmpdir, base) + '.stderr'

        failed = False
        fail_reason = None
        job_result = {'payload': base}

        try:
            with open(stdout_file, 'wb') as stdout, open(stderr_file, 'wb') as stderr:
                runpg(
                    [payload_file, *args],
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
                # DynamoDB didn't use to be able to habdle empty strings.
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

    return return_info
