"""Lava specific common functions."""

from __future__ import annotations

import json
import logging
import os
import sys
import traceback
from pathlib import Path
from shutil import rmtree
from tempfile import mkdtemp
from time import sleep
from typing import Any, Callable

import boto3
import jinja2
from dateutil.tz import UTC

from lava.actions import do_actions
from lava.config import LOGNAME, config
from lava.event import log_event
from lava.lavacore import LavaError, jinja_render_vars
from lava.lib.aws import s3_split
from lava.lib.datetime import duration_to_seconds, now_tz
from lava.lib.decorators import deprecated
from lava.lib.misc import import_by_name, size_to_bytes, str2bool
from lava.lib.state import LavaStateItem

__author__ = 'Murray Andrews'

LOG = logging.getLogger(name=LOGNAME)


# ------------------------------------------------------------------------------
def run_job(
    job_spec: dict[str, Any],
    realm_info: dict[str, Any],
    tmpdir: str | Path,
    cleanup: bool = True,
    dev_mode: bool = False,
    aws_session: boto3.Session = None,
) -> dict[str, Any]:
    """
    Run a job.

    :param job_spec:        The job spec.
    :param realm_info:      The realm info.
    :param tmpdir:          Temp directory. If cleanup is true a sub-directory
                            will be created in here for job use. This must
                            already exist.
    :param cleanup:         If True cleanup any job temp directories created.
                            Default True.
    :param aws_session:     A boto3 Session()
    :param dev_mode:        Passed to the job handler. Its up to the handler to
                            decide what it does with this. Default False.

    return:                 The result produced by the job.

    :raise LavaError:   If the job fails.

    """

    job_id = job_spec['job_id']
    run_id = job_spec['run_id']
    realm = job_spec['realm']
    result = {}

    cw = None
    cw_metrics = job_spec.get('cw_metrics', config('CW_METRICS_JOB', str2bool))

    if cw_metrics:
        cw = aws_session.client('cloudwatch')

    # ----------------------------------------
    # Check if the job is enabled with a simple boolean.

    enabled = job_spec['enabled']
    if isinstance(enabled, bool) and not enabled:
        LOG.warning(
            f'Job {job_id} ({run_id}): Job is not enabled (static)',
            extra={'event_type': 'job', 'job_id': job_id, 'run_id': run_id},
        )
        log_event(job_spec, 'skipped', info='Job not enabled (static)')
        return result

    # ----------------------------------------
    # Add some timestamps to the job spec -- typically used in jinja rendering.

    LOG.info(
        f'Job {job_id} ({run_id}): Starting',
        extra={'event_type': 'job', 'job_id': job_id, 'run_id': run_id},
    )
    ts_start = log_event(job_spec, 'starting')
    ts_ustart = ts_start.astimezone(UTC)
    job_spec['ts_start'] = ts_start
    job_spec['ts_ustart'] = ts_ustart

    # ----------------------------------------
    # Make sure the dispatch event is not too old.

    max_run_delay = job_spec.get('max_run_delay')
    if max_run_delay:
        try:
            max_run_delay_s = duration_to_seconds(max_run_delay)
        except ValueError:
            err = f'Bad max_run_delay: {max_run_delay}'
            log_event(job_spec, 'rejected', err)
            raise LavaError(err)
        if (ts_start - job_spec['ts_dispatch']).total_seconds() > max_run_delay_s:
            err = f'dispatch is more than {max_run_delay} old'
            log_event(job_spec, 'rejected', err)
            raise LavaError(err)

    # ----------------------------------------
    # Prepare for job retries (iterations)

    iteration_limit = int(job_spec.get('iteration_limit', 1))
    iteration_limit_max = config('ITERATION_MAX_LIMIT', int)
    if iteration_limit > iteration_limit_max:
        err = f'iteration_limit must be <= {iteration_limit_max}'
        log_event(job_spec, 'rejected', err)
        raise LavaError(err)

    iteration_delay = duration_to_seconds(job_spec.get('iteration_delay', 0))
    iteration_delay_max = config('ITERATION_MAX_DELAY')
    if iteration_delay > duration_to_seconds(iteration_delay_max):
        err = f'iteration_delay must be <= {iteration_delay_max}'
        log_event(job_spec, 'rejected', err)
        raise LavaError(err)

    # ----------------------------------------
    # Fiddle with lava's reserved globals. These may have been set in an
    # upstream chain job.

    lava_globals = job_spec['globals'].setdefault('lava', {})
    lava_globals.setdefault('master_job_id', job_spec['job_id'])
    lava_globals.setdefault('parent_job_id', job_spec['job_id'])

    lava_globals.setdefault('master_start', ts_start)
    lava_globals.setdefault('master_ustart', ts_ustart)
    lava_globals.setdefault('parent_start', ts_start)
    lava_globals.setdefault('parent_ustart', ts_ustart)

    # ----------------------------------------
    # Populate the state map. Missing values are not an error.
    state = job_spec['state']
    for k in state:
        try:
            state[k] = LavaStateItem.get(k, realm, aws_session=aws_session).value
        except KeyError:
            LOG.debug('%s: No such state item', k)

    # ----------------------------------------
    # Add some custom stuff into the event log.
    # New in v7.1.0.
    stuff_to_log = job_spec.get('event_log')
    render_vars = jinja_render_vars(job_spec, realm_info)
    if stuff_to_log:
        try:
            # This is a hack to Jinja render a more or less arbitrary object.
            event_info = json.loads(
                jinja2.Template(json.dumps(stuff_to_log, indent=1)).render(**render_vars)
            )
        except Exception as e:
            # We don't consider a failure to log stuff as a fatal error
            LOG.error(
                f'Job {job_id} ({run_id}): Bad event_log: {e}',
                extra={'event_type': 'job', 'job_id': job_id, 'run_id': run_id},
            )
            event_info = f'Error: Bad event_log: {e}'
        log_event(job_spec, 'logging', info=event_info)

    # ----------------------------------------
    # Check if the job is dynamically eneabled.
    if (
        isinstance(enabled, str)
        and (e := jinja2.Template(enabled).render(**render_vars).strip().lower()) != 'true'
    ):
        LOG.warning(
            f'Job {job_id} ({run_id}): Job is not enabled (dynamic)',
            extra={'event_type': 'job', 'job_id': job_id, 'run_id': run_id, 'enabled': e},
        )
        log_event(job_spec, 'skipped', info=f'Job not enabled (enabled="{e}")')
        return result

    # ----------------------------------------
    if cw_metrics:
        LOG.debug('Sending CloudWatch metrics for job run delay')
        try:
            cw.put_metric_data(
                Namespace=config('CW_NAMESPACE'),
                MetricData=[
                    {
                        'MetricName': 'RunDelay',
                        'Value': (ts_start - job_spec['ts_dispatch']).total_seconds(),
                        'Unit': 'Seconds',
                        'Dimensions': [
                            {'Name': 'Realm', 'Value': realm},
                            {'Name': 'Worker', 'Value': job_spec['worker']},
                        ],
                        'Timestamp': job_spec['ts_dispatch'],  # Questionable
                    },
                ],
            )
        except Exception as e:
            err = f'Can\'t put metric data: {e}'
            log_event(job_spec, 'failed', info=err)
            raise LavaError(err)

    # Import a handler
    try:
        handler = get_job_handler(job_spec['type'])
    except LavaError as e:
        log_event(job_spec, 'failed', info=str(e))
        raise

    if cleanup:
        job_tmpdir = os.path.join(tmpdir, run_id)
        if os.path.exists(job_tmpdir):
            # Two dispatches of the same job have crashed into each other
            raise LavaError('Job temp dir already exists - possible dispatch overlap')
        os.makedirs(job_tmpdir)
    else:
        # We're allowed to use the tmpdir directly for the job
        job_tmpdir = tmpdir

    # ----------------------------------------
    # Run the handler

    fatal: Exception | None = None

    for iteration in range(1, iteration_limit + 1):
        lava_globals['iteration'] = iteration

        LOG.info(
            f'Job {job_id} ({run_id}): Running iteration {iteration}',
            extra={'event_type': 'job', 'job_id': job_id, 'run_id': run_id},
        )
        log_event(job_spec, 'running', info=f'Iteration {iteration}')

        try:
            result = _run_job_once(
                handler=handler,
                job_spec=job_spec,
                realm_info=realm_info,
                can_retry=(iteration < iteration_limit),
                tmpdir=job_tmpdir,
                dev_mode=dev_mode,
                aws_session=aws_session,
            )
        except Exception as e:
            LOG.error(
                f'Job {job_id} ({run_id}): Iteration {iteration} failed: {e}',
                extra={'event_type': 'job', 'job_id': job_id, 'run_id': run_id},
            )
            fatal = e
            if iteration < iteration_limit:
                LOG.info(
                    f'Job {job_id} ({run_id}): Will retry in {iteration_delay} seconds',
                    extra={'event_type': 'job', 'job_id': job_id, 'run_id': run_id},
                )
                sleep(iteration_delay)
        else:
            # Success
            fatal = None
            result.setdefault('error')
            break
    else:
        if iteration_limit > 1:
            LOG.error(
                f'Job {job_id} ({run_id}): Failed {iteration_limit} times - abort',
                extra={'event_type': 'job', 'job_id': job_id, 'run_id': run_id},
            )

    # ----------------------------------------
    # Put CloudWatch metrics for the job
    if cw_metrics:
        LOG.debug('Sending CloudWatch metrics for job completion')
        dimensions = [{'Name': 'Realm', 'Value': realm}, {'Name': 'Job', 'Value': job_id}]

        cw.put_metric_data(
            Namespace=config('CW_NAMESPACE'),
            MetricData=[
                {
                    # RunTime
                    'MetricName': 'RunTime',
                    'Value': (now_tz() - ts_start).total_seconds(),
                    'Unit': 'Seconds',
                    'Dimensions': dimensions,
                    'Timestamp': job_spec['ts_dispatch'],  # Questionable
                },
                {
                    # Success/fail metric
                    'MetricName': 'JobFailed',
                    'Value': 1.0 if fatal else 0.0,
                    'Dimensions': dimensions,
                    'Timestamp': job_spec['ts_dispatch'],  # Questionable
                },
            ],
        )

    # ----------------------------------------
    LOG.debug('Result: %s', result)

    if cleanup:
        try:
            rmtree(job_tmpdir, ignore_errors=True)
        except Exception as e:
            LOG.warning(
                f'Job {job_id} ({run_id}): While cleaning temp dir: {e}',
                extra={'event_type': 'job', 'job_id': job_id, 'run_id': run_id},
            )
            raise

    if fatal:
        raise fatal

    return result


# ------------------------------------------------------------------------------
def _run_job_once(
    handler: Callable,
    job_spec: dict[str, Any],
    realm_info: dict[str, Any],
    can_retry: bool,
    tmpdir: str,
    dev_mode: bool,
    aws_session: boto3.Session,
) -> dict[str, Any]:
    """
    Run a lava job once.

    Lava internal use only.

    :param handler:         The job handler.
    :param job_spec:        The job spec.
    :param realm_info:      The realm info.
    :param can_retry:       If True job can be retried by the caller if it fails.
    :param tmpdir:          Name of tmp dir. Must exist.
    :param dev_mode:        Passed to the job handler. Its up to the handler to
                            decide what it does with this. Default False.
    :param aws_session:     A boto3 Session()

    :return:                The job result
    :raise LavaError:       If the job fails.
    """

    job_id = job_spec['job_id']
    run_id = job_spec['run_id']

    result = {}
    try:
        result = handler(
            job_spec=job_spec,
            realm_info=realm_info,
            tmpdir=tmpdir,
            s3tmp=realm_info['s3_temp'] + '/' + job_id + '/' + run_id,
            dev_mode=dev_mode,
            aws_session=aws_session,
        )  # type: dict
    except Exception as e:
        if not isinstance(e, LavaError):
            e = LavaError(str(e))

        result['error_data'] = e.data
        result['error'] = str(e)
        if config('DEBUG', str2bool):
            # Log the traceback
            result['exception'] = traceback.format_exception(*sys.exc_info())

        log_event(job_spec, 'retrying' if can_retry else 'failed', info=result)

        # Run on_fail or on_retry actions
        try:
            do_actions(
                'on_retry' if can_retry else 'on_fail',
                job_spec,
                realm_info,
                job_result=result,
                aws_session=aws_session,
            )
        except Exception as ex:
            LOG.error(
                f'Job {job_id} ({run_id}): Action failed: {ex}',
                extra={'event_type': 'job', 'job_id': job_id, 'run_id': run_id},
            )
            log_event(job_spec, 'action_failed', str(ex))
        raise e

    # ------------------------------
    # Success!
    LOG.info(
        f'Job {job_id} ({run_id}): Complete',
        extra={'event_type': 'job', 'job_id': job_id, 'run_id': run_id},
    )
    log_event(job_spec, 'complete', info=result)

    # Run on_success actions
    try:
        do_actions('on_success', job_spec, realm_info, job_result=result, aws_session=aws_session)
    except Exception as ex:
        LOG.error(
            f'Job {job_id} ({run_id}): Action failed: {ex}',
            extra={'event_type': 'job', 'job_id': job_id, 'run_id': run_id},
        )
        log_event(job_spec, 'action_failed', str(ex))

    return result


# ------------------------------------------------------------------------------
def get_payload_from_s3(*args, **kwargs) -> list[str]:
    """
    Allow selection of the v1 or v2 payload downloader.

    Because this depends on a config item, it has to be decided at run-time due
    to the need to check the realms table for config.

    Once a realm has upgraded from v1 to v2, you can't really go back again as
    jobs may be taking advantage of the extra capability.

    :param args:        Passed through.
    :param kwargs:      Passed through.
    :return:            A sorted list of full local pathnames.
    """

    ver = config('PAYLOAD_DOWNLOADER')
    LOG.debug('Using %s payload downloader', ver)

    if ver == 'v2':
        return get_payload_from_s3_v2(*args, **kwargs)

    if ver == 'v1':
        return get_payload_from_s3_v1(*args, **kwargs)

    raise LavaError(f'Unknown PAYLOAD_DOWNLOADER: {ver}')


# ------------------------------------------------------------------------------
@deprecated('Use `get_payload_from_s3_v2()`')
def get_payload_from_s3_v1(
    payload: str,
    realm_info: dict[str, Any],
    local_dir: str,
    max_size: int | str = None,
    aws_session: boto3.Session = None,
) -> list[str]:
    """
    Retrieve the payload for the given job from S3 to the specified directory.

    !!! warning "Deprecated as of v8.1.0"
        This will be removed soon. Use `get_payload_from_s3_v2()`.

    This handles case where the payload specifies a prefix as well as a single
    object. Any objects with a zero length basename are skipped as these are
    crap left behind by the AWS console.

    :param payload:         The payload name relative to the payloads area for
                            the given realm.
    :param realm_info:      Realm information.
    :param local_dir:       A local directory. Must exist.
    :param max_size:        If the object size is bigger than this then don't
                            download. See size_to_bytes() for allowed values.
                            Values like 40K, 20M, 5GiB are accepted.
    :param aws_session:     A boto3 Session().

    :return:                A sorted list of full local pathnames.
    """

    if not isinstance(payload, str):
        raise LavaError(f'Payload must be string not {type(payload)}')

    if not aws_session:
        aws_session = boto3.Session()

    s3_client = aws_session.client('s3')

    bucket, prefix = s3_split(realm_info['s3_payloads'])
    payload_prefix = prefix + '/' + payload

    try:
        max_size_n = size_to_bytes(max_size) if max_size is not None else None
    except Exception as e:
        raise LavaError(f's3://{bucket}/{payload_prefix}: {e}')

    paginator = s3_client.get_paginator('list_objects_v2')

    local_files = []

    LOG.debug(f'Scanning s3://{bucket}/{payload_prefix}')

    # List the given S3 prefix (no recursion)
    for result in paginator.paginate(Bucket=bucket, Prefix=payload_prefix, Delimiter='/'):
        if result.get('CommonPrefixes') is not None:
            raise LavaError(f's3://{bucket}/{payload_prefix}: Recursive download not supported')

        for item in result.get('Contents', []):
            payload_key = item['Key']

            # Skip objects with zero length basename
            if not payload_key.rsplit('/', 1)[-1]:
                LOG.debug('Skipping dud file: %s', payload_key)
                continue

            # Make sure object is not too big
            if max_size_n and item['Size'] > max_size_n:
                raise LavaError(
                    f's3://{bucket}/{payload_key}:'
                    f' Payload size {item["Size"]} exceeds maximum of {max_size}'
                )

            # Download it
            local_file = os.path.join(local_dir, os.path.basename(payload_key))
            with open(local_file, 'wb') as fp:
                s3_client.download_fileobj(bucket, payload_key, fp)
                # This is meant to solve the intermittent "Text File Busy"
                # exception that can occur if the download is for an executable
                # which is then executed in a subprocess via Popen().
                fp.flush()
                os.fsync(fp.fileno())

            local_files.append(local_file)
            LOG.debug(f'Downloaded s3://{bucket}/{payload_key} to {local_file}')

    if not local_files:
        raise LavaError('No payload files downloaded from S3')

    # Final defence against Text File Busy issue which occurs when trying to
    # execute a downloaded script too quickly in a new process via Popen().
    sleep(config('PAYLOAD_SETTLING_TIME', int))

    return sorted(local_files)


# ------------------------------------------------------------------------------
def get_payload_from_s3_v2(
    payload: str | list[str],
    realm_info: dict[str, Any],
    local_dir: str,
    max_size: int | str = None,
    aws_session: boto3.Session = None,
) -> list[str]:
    """
    Retrieve the payload for the given job from S3 to the specified directory.

    This handles case where the payload specifies a prefix as well as a single
    object. Any objects with a zero length basename are skipped as these are
    crap left behind by the AWS console.

    :param payload:         The payload name relative to the payloads area for
                            the given realm.
    :param realm_info:      Realm information.
    :param local_dir:       A local directory. Must exist.
    :param max_size:        If the object size is bigger than this then don't
                            download. See size_to_bytes() for allowed values.
                            Values like 40K, 20M, 5GiB are accepted.
    :param aws_session:     A boto3 Session().

    :return:                A sorted list of full local pathnames.
    """

    if not isinstance(payload, (str, list)):
        raise LavaError(f'Payload must be string or list[string] not {type(payload)}')

    if not isinstance(payload, list):
        payload = [payload]

    s3 = (aws_session or boto3.Session()).resource('s3')

    try:
        max_size_n = size_to_bytes(max_size) if max_size is not None else None
    except Exception as e:
        raise LavaError(f'Bad max_size {max_size} for payload: {e}')

    bucket, realm_prefix = s3_split(realm_info['s3_payloads'])
    s3bucket = s3.Bucket(bucket)

    local_files = []

    for n, p in enumerate(payload):
        payload_prefix = f'{realm_prefix}/{p}'
        LOG.debug(f'Scanning s3://{bucket}/{payload_prefix}')
        payload_dir = Path(mkdtemp(prefix=f'pld-{n}-', suffix='.d', dir=local_dir))
        local_files_per_prefix = []
        for s3obj in s3bucket.objects.filter(Prefix=payload_prefix, Delimiter='/'):
            LOG.debug('Found payload object: %s', s3obj.key)

            # Skip objects with zero length basename
            if s3obj.key.endswith('/'):
                LOG.debug('Skipping dud file: %s', s3obj.key)
                continue

            # Make sure object is not too big
            if max_size_n and s3obj.size > max_size_n:
                raise LavaError(
                    f's3://{bucket}/{s3obj.key}:'
                    f' Payload size {s3obj.size} exceeds maximum of {max_size}'
                )

            # Download
            local_path = payload_dir / Path(s3obj.key).name
            with local_path.open('wb') as fp:
                s3bucket.download_fileobj(s3obj.key, fp)
                # This is meant to solve the intermittent "Text File Busy"
                # exception that can occur if the download is for an executable
                # which is then executed in a subprocess via Popen().
                fp.flush()
                os.fsync(fp.fileno())
            LOG.debug(f'Downloaded s3://{bucket}/{s3obj.key} to {local_path}')
            local_files_per_prefix.append(str(local_path))

        if not local_files_per_prefix:
            raise LavaError(f'No payload files downloaded from S3 for payload: {p}')

        local_files.extend(sorted(local_files_per_prefix))

    # Final defence against Text File Busy issue which occurs when trying to
    # execute a downloaded script too quickly in a new process via Popen().
    sleep(config('PAYLOAD_SETTLING_TIME', int))

    return local_files


# ------------------------------------------------------------------------------
def get_job_handler(job_type: str) -> Callable:
    """
    Get a handler function for a given job type.

    :param job_type:    The job type.
    :return:            A run() function for the job type.
    """

    try:
        handler_module = import_by_name(job_type, parent='lava.handlers')
    except (ImportError, ModuleNotFoundError):
        raise LavaError(f'{job_type}: Unknown job type')

    try:
        handler = handler_module.run
    except AttributeError:
        raise LavaError(f'{job_type}: Bad job handler -- no run() function')

    if not callable(handler):
        raise LavaError(f'{job_type}: Bad job hamdler -- run() is not callable')

    return handler
