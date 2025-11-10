"""Low level lava primitives."""

from __future__ import annotations

import json
import logging
import os.path
import re
import threading
from collections.abc import Iterable
from datetime import date, datetime, time, timedelta, timezone
from fnmatch import fnmatchcase
from threading import Lock
from typing import Any
from uuid import uuid4

import boto3
import dateutil.parser
import jinja2

from lava.lib.aws import dynamo_unmarshall_item, s3_split, sqs_send_msg
from lava.lib.datetime import DT_MAX, DT_MIN, now_tz, parse_dt
from lava.lib.misc import dict_check, json_default

__author__ = 'Murray Andrews'

LOGNAME = 'lava'  # Set to None to include boto which uses root logger.
LOG = logging.getLogger(name=LOGNAME)

JOB_SPEC_REQUIRED_FIELDS = {'job_id', 'type', 'worker', 'payload'}
JOB_SPEC_OPTIONAL_FIELDS = {
    'cw_metrics',
    'description',
    'dispatcher',
    'enabled',
    'event_log',
    'globals',
    'iteration_delay',
    'iteration_limit',
    'max_run_delay',
    'max_tries',
    'on_fail',
    'on_retry',
    'on_success',
    'owner',
    'parameters',
    'schedule',
    'state',
}
REALM_REQUIRED_FIELDS = {'realm', 's3_payloads', 's3_temp'}

SCHEDULE_REQUIRED_FIELDS = {'crontab'}
SCHEDULE_OPTIONAL_FIELDS = {'from', 'to'}

IGNORE_FIELDS = {'X-*', 'x-*'}

# This is made available to the Jinja2 renderer via the utils var.
JINJA_UTILS = {
    'timedelta': timedelta,
    'datetime': datetime,
    'date': date,
    'dateutil': dateutil,
    'time': time,
    'parsedate': dateutil.parser,
    's3bucket': lambda s: s3_split(s)[0],
    's3key': lambda s: s3_split(s)[1],
    'uuid': uuid4,
    'path': os.path,
    're': re,
}

DEFER_ON_EXIT = 'atexit'


# ------------------------------------------------------------------------------
def scan_realms(
    attributes: Iterable[str] = None, aws_session: boto3.Session = None
) -> dict[str, dict[str, str]]:
    """
    Scan the available realms.

    :param attributes:  An iterable of attribute names to return. If None then
                        just the realm name will be returned. The realm name is
                        always included no what is requested.
    :param aws_session: A boto3 Session(). If not specified, a default
                        session will be created.

    :return:            A dictionary mapping realm name to selected realm
                        attributes.
    """

    if not aws_session:
        aws_session = boto3.Session()

    attribute_expr_names = {f'#{name}': name for name in attributes} if attributes else {}
    attribute_expr_names['#realm'] = 'realm'

    dynamo = aws_session.client('dynamodb')
    paginator = dynamo.get_paginator('scan')

    response_iterator = paginator.paginate(
        TableName='lava.realms',
        ProjectionExpression=','.join(attribute_expr_names),
        ExpressionAttributeNames=attribute_expr_names,
    )

    items = []
    for response in response_iterator:
        items.extend(response['Items'])

    return {i['realm']['S']: dynamo_unmarshall_item(i) for i in items}


# ------------------------------------------------------------------------------
def scan_jobs(
    realm: str, attributes: Iterable[str] = None, aws_session: boto3.Session = None
) -> dict[str, dict[str, str]]:
    """
    Scan a realm for jobs.

    :param realm:       Realm name
    :param attributes:  An iterable of attribute names to return. If None then
                        just the job name will be returned. The job name is
                        always included no matter what is requested.
    :param aws_session: A boto3 Session(). If not specified, a default
                        session will be created.

    :return:            A dictionary mapping job name to selected job
                        attributes.
    """

    if not aws_session:
        aws_session = boto3.Session()

    attribute_expr_names = {f'#{name}': name for name in attributes} if attributes else {}
    attribute_expr_names['#job_id'] = 'job_id'

    dynamo = aws_session.client('dynamodb')
    paginator = dynamo.get_paginator('scan')

    response_iterator = paginator.paginate(
        TableName=f'lava.{realm}.jobs',
        ProjectionExpression=','.join(attribute_expr_names),
        ExpressionAttributeNames=attribute_expr_names,
    )

    items = []
    for response in response_iterator:
        items.extend(response['Items'])

    return {i['job_id']['S']: dynamo_unmarshall_item(i) for i in items}


# ------------------------------------------------------------------------------
def get_realm_info(realm: str, realm_table) -> dict[str, Any]:
    """
    Get the realm record from DynamoDB for the given realm.

    :param realm:           The realm.
    :param realm_table:     DynamoDB realm table resource.

    :return:                The realm specification.

    """

    try:
        realm_info = realm_table.get_item(Key={'realm': realm})['Item']  # type:dict
    except KeyError:
        raise LavaError('No such realm')

    LOG.debug(f'Realm info: {realm_info}')

    try:
        dict_check(realm_info, required=REALM_REQUIRED_FIELDS, ignore=IGNORE_FIELDS)
    except ValueError as e:
        raise LavaError(f'Bad realm record: {e}')

    return realm_info


# ------------------------------------------------------------------------------
def get_job_spec(job_id: str, jobs_table) -> dict[str, Any]:
    """
    Get the job spec from the DynamoDB table.

    :param job_id:      Job ID.
    :param jobs_table:  DynamoDB jobs table resource.

    :return:            The job spec.

    """

    try:
        job_spec = jobs_table.get_item(Key={'job_id': job_id})['Item']  # type:dict
    except KeyError:
        raise LavaError('No such job')

    try:
        dict_check(job_spec, required=JOB_SPEC_REQUIRED_FIELDS, ignore=IGNORE_FIELDS)
    except ValueError as e:
        raise LavaError(f'Bad job record: {e}')

    # Historically we have not aborted on bad optional keys in the job spec.
    # For now, this is a deprecation warning. Future releases will make this a
    # hard fail.
    try:
        dict_check(
            job_spec,
            required=JOB_SPEC_REQUIRED_FIELDS,
            optional=JOB_SPEC_OPTIONAL_FIELDS,
            ignore=IGNORE_FIELDS,
        )
    except ValueError as e:
        LOG.warning(
            f'{job_id}: Job spec deprecation warning: {e}',
            extra={
                'event_type': 'job',
                'job_id': job_spec['job_id'],
                'run_id': job_spec.get('run_id'),
            },
        )

    # Owner will become mandatory in a future release
    if not job_spec.get('owner'):
        job_spec['owner'] = ''
        LOG.warning(
            f'{job_id}: Job spec deprecation warning:'
            f' owner field will be mandatory in a future release',
            extra={
                'event_type': 'job',
                'job_id': job_spec['job_id'],
                'run_id': job_spec.get('run_id'),
            },
        )

    # Description will become mandatory in a future release
    if not job_spec.get('description'):
        job_spec['description'] = ''
        LOG.warning(
            f'{job_id}: Job spec deprecation warning:'
            f' description field will be mandatory in a future release',
            extra={
                'event_type': 'job',
                'job_id': job_spec['job_id'],
                'run_id': job_spec.get('run_id'),
            },
        )

    LOG.debug(f'Job record: {job_spec}')

    # Set defaults for some optional elements
    job_spec.setdefault('enabled', False)
    job_spec.setdefault('max_tries', 0)
    if not job_spec.get('parameters'):
        job_spec['parameters'] = {}

    # Create a detault globals structure
    if not job_spec.get('globals'):
        job_spec['globals'] = {}

    # Make sure no reserved global names are used
    for g in job_spec['globals']:  # type: str
        if g.lower().startswith('lava'):
            raise LavaError(f'Reserved global: {g}')

    # Create a detault state structure
    job_spec.setdefault('state', {})

    return job_spec


# ------------------------------------------------------------------------------
class LavaError(Exception):
    """
    Lava specific exception.

    :param data:    Any JSON serialisable object.
    """

    def __init__(self, *args, data: Any = None, **kwargs):
        """Create a LavaError."""

        # noinspection PyArgumentList
        super().__init__(*args, **kwargs)
        self.data = data


# For backward compatibility ... for now
LavaException = LavaError


# ------------------------------------------------------------------------------
def jinja_render_vars(
    job_spec: dict[str, Any], realm_info: dict[str, Any], **kwargs
) -> dict[str, Any]:
    """
    Set up common elements for Jinja rendering.

    :param realm_info:  Realm spec.
    :param job_spec:    Augmented job spec.
    :param kwargs:      Extras to add.
    :return:            A dictionary to be fed to the Jinja template renderer.
    """

    return dict(
        job=job_spec,
        realm=realm_info,
        globals=job_spec['globals'],
        start=job_spec['ts_start'],
        state=job_spec['state'],
        ustart=job_spec['ts_start'].astimezone(timezone.utc),
        utils=JINJA_UTILS,
        **kwargs,
    )


# ------------------------------------------------------------------------------
def job_environment(
    job_spec: dict[str, Any],
    realm_info: dict[str, Any],
    base: dict[str, str],
    render_vars: dict[str, Any] = None,
    **kwargs,
) -> dict[str, str]:
    """
    Prepare a basic environment package for a job handler.

    The order of precedence is (lowest to highest):

    1.  The base environment
    2.  The environment from the job spec.
    3.  The extras (kwargs)
    4.  The lava internally specified vars.

    It's up to the job handler to apply this when the job runs. The handler is
    free to enhance this as appropriate.

    :param realm_info:  Realm spec.
    :param job_spec:    Augmented job spec.
    :param base:        A base starting set of variables.
    :param render_vars: If specified, Jinja render any environment values in the
                        job spec with these values.
    :param kwargs:      Extras to add.

    :return:            A dict of environment variables.
    """

    # Start with a copy of the worker environment
    env = base or {}

    # Render and add the job spec environment
    if render_vars:
        job_env = job_spec.get('parameters', {}).get('env', {})
        for k, v in job_env.items():
            try:
                env[k] = jinja2.Template(v).render(**render_vars)
            except Exception as e:
                raise LavaError(f'Bad environment variable: {k}: {e}')

    # Add the extrra. Order of precedence is important here.
    env.update(kwargs)

    # Add some system environment vars
    env.update(
        {
            'LAVA_REALM': job_spec['realm'],
            'LAVA_WORKER': job_spec['worker'],
            'LAVA_OWNER': job_spec['owner'],
            'LAVA_JOB_ID': job_spec['job_id'],
            'LAVA_RUN_ID': job_spec['run_id'],
            'LAVA_S3_KEY': realm_info.get('s3_key'),
        }
    )

    return env


# ------------------------------------------------------------------------------
class JobSchedule:
    """
    Represents a lava job schedule.

     This is essentially:

        - A crontab spec
        - A valid "from" datetime (defaults to year 1)
        - A valid "to" datetime (defaults to year 9999)

    :param sched:       Either a string or a dict containing schedule
                        details: crontab and optional from, to.
    """

    # --------------------------------------------------------------------------
    def __init__(self, sched: str | dict[str, str]) -> None:
        """Create a JobSchedule instance."""

        self.valid_from = DT_MIN
        self.valid_to = DT_MAX

        # If it's a string -- its a crontab valid forever.
        if isinstance(sched, str):
            self.crontab = sched.strip()
            return

        if not isinstance(sched, dict):
            raise LavaError(f'Expected dict, got {type(sched)}')

        # We have a schedule dict - maybe with valid_from / valid_to
        try:
            dict_check(sched, required=SCHEDULE_REQUIRED_FIELDS, optional=SCHEDULE_OPTIONAL_FIELDS)
        except ValueError as e:
            raise LavaError(str(e))

        self.crontab = sched['crontab'].strip()
        # Convert valid_from and valid_to
        try:
            self.valid_from = parse_dt(sched['from'])
        except KeyError:
            pass
        except Exception as e:
            raise LavaError(f'Bad "from"": {e}')

        # Convert valid_from and valid_to
        try:
            self.valid_to = parse_dt(sched['to'])
        except KeyError:
            pass
        except Exception as e:
            raise LavaError(f'Bad "to"": {e}')

    # --------------------------------------------------------------------------
    def __str__(self) -> str:
        """Printable representation."""

        if self.valid_from <= self.valid_to:
            return f'{self.crontab}: {self.valid_from} --> {self.valid_to}'

        return f'{self.crontab}: --> {self.valid_to} // {self.valid_from} -->'

    # --------------------------------------------------------------------------
    @property
    def active(self) -> bool:
        """
        Determine if the schedule is active right now.

        A given job schedule is active if either:

            - from <= now <= to
              or
            - from > to and (now <= to or now >= from)

        i.e. If from < to then current time must be between them otherwise it
        must not be between them. This allows inclusion and exclusion ranges to
        be specified.

        :return:        True if the schedule is active.
        """

        now = now_tz()

        return (self.valid_from <= now <= self.valid_to) or (
            self.valid_from > self.valid_to and (now <= self.valid_to or now >= self.valid_from)
        )


# ------------------------------------------------------------------------------
def dispatch(
    realm: str,
    job_id: str,
    worker: str = None,
    params: dict[str, Any] = None,
    delay: int = 0,
    queue_name: str = None,
    aws_session: boto3.Session = None,
    globals_: dict[str, Any] = None,
) -> str:
    """
    Send a dispatch message for the specified realm / job.

    :param realm:           The realm name.
    :param job_id:          The ID of the job to dispatch.
    :param worker:          The target worker name. If not specified, look up
                            the worker name in the job table.
    :param params:          An optional dictionary of parameters to include in
                            the dispatch.
    :param globals_:        An optional dictionary of global attributes to
                            include in the dispatch.
    :param delay:           Delay in seconds for the dispatch SQS message. This
                            delay is handled by SQS itself and is thus limited
                            to values acceptable to SQS. Default is 0.
    :param queue_name:      Name of the dispatch SQS queue. If not specified,
                            the value is derived from the realm and worker
                            names. It should almost never be specified.
                            Default None.
    :param aws_session:     A boto3 Session object. If not specified, a default is
                            created.

    :return:                The run ID.

    """

    if not aws_session:
        aws_session = boto3.Session()

    if not worker:
        # Extract the target worker name from the DB
        jobs_table_name = f'lava.{realm}.jobs'

        try:
            jobs_table = aws_session.resource('dynamodb').Table(jobs_table_name)
        except Exception as e:
            raise LavaError(f'Cannot get DynamoDB table {jobs_table_name} - {e}')

        job_spec = get_job_spec(job_id, jobs_table)
        worker = job_spec['worker']

    # ----------------------------------------
    # Prepare the dispatch message

    dispatch_msg = {
        'realm': realm,
        'worker': worker,
        'job_id': job_id,
        'run_id': str(uuid4()),
        'ts_dispatch': now_tz().isoformat(),
    }

    if params:
        if not isinstance(params, dict):
            raise LavaError('parameters must be a dict')
        dispatch_msg['parameters'] = params

    if globals_:
        if not isinstance(globals_, dict):
            raise LavaError('globals must be a dict')
        dispatch_msg['globals'] = globals_

    # ----------------------------------------
    # Send it
    if not queue_name:
        queue_name = f'lava-{realm}-{worker}'
    LOG.debug(f'Dispatching {job_id} to queue {queue_name}')
    LOG.debug(f'Message body for {job_id} is {dispatch_msg}')
    try:
        sqs_send_msg(json.dumps(dispatch_msg, default=json_default), queue_name, int(delay))
    except Exception as e:
        raise LavaError(f'Cannot dispatch {job_id}@{realm} - {e}')

    return dispatch_msg['run_id']


# ------------------------------------------------------------------------------
class ThreadMonitor:
    """Singleton class to monitor thread health."""

    thread_register = {}
    thread_register_lock = Lock()

    # --------------------------------------------------------------------------
    def __new__(cls):
        """Make sure this is a singleton."""
        if not hasattr(cls, 'instance'):
            cls.instance = super().__new__(cls)
        # noinspection PyUnresolvedReferences
        return cls.instance

    # --------------------------------------------------------------------------
    def register_thread(self, thread: threading.Thread = None) -> None:
        """
        Register the named thread as one to keep an eye on.

        :param thread:  The thread to register. Defaults to the current thread.
        """

        if not thread:
            thread = threading.current_thread()
        with self.thread_register_lock:
            self.thread_register[thread.name] = thread.is_alive()
        LOG.debug('Thread %s registered for monitoring', thread.name)

    # --------------------------------------------------------------------------
    def check_threads(self):
        """
        Check the health status of threads and update the thread register.

        :return:    A list of the names of any threads that have died since last
                    check.
        """

        with self.thread_register_lock:
            live_threads = {t.name for t in threading.enumerate() if t.is_alive()}
            for thread_name, was_ok in self.thread_register.items():
                if was_ok and thread_name not in live_threads:
                    # Was alive before and is now dead
                    LOG.critical('Thread %s has died', thread_name, extra={'event_type': 'worker'})
                    self.thread_register[thread_name] = False
                elif not was_ok and thread_name in live_threads:
                    # Was dead before and is now alive -- It's a miracle!
                    LOG.info('Thread %s is now alive', thread_name, extra={'event_type': 'worker'})
                    self.thread_register[thread_name] = True

    # --------------------------------------------------------------------------
    def threadcount(self, name_glob: str) -> tuple[int, int]:
        """
        Get counts of threads with names matching the specified pattern.

        :return:    A tuple of counts (live threads, dead threads)
        """

        self.check_threads()
        threads = [
            int(is_alive)
            for name, is_alive in self.thread_register.items()
            if fnmatchcase(name, name_glob)
        ]
        return (live_count := sum(threads)), len(threads) - live_count

    # --------------------------------------------------------------------------
    @property
    def thread_status(self) -> dict[str, str]:
        """Get current status of the threads."""
        self.check_threads()
        return {name: 'OK' if stat else 'dead' for name, stat in self.thread_register.items()}
