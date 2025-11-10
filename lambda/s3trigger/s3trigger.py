"""
Lambda function to allow an S3 event to trigger a Lava dispatch.

This supports incoming S3 events via:

-   Direct subscription
-   SNS
-   SQS
-   EventBridge

The first 3 all have different wrappers but the same basic core message
structure. EventBridge has different wrapping (basically none) and a different
message format. It's a joke.

"""

from __future__ import annotations

import json
import logging
import os
from datetime import datetime
from fnmatch import fnmatch
from threading import RLock
from typing import Any, Callable
from urllib.parse import unquote_plus

import boto3
import jinja2
from cachetools import TTLCache, cached

from lava.config import LOGLEVEL, LOGNAME, config
from lava.lavacore import IGNORE_FIELDS, JINJA_UTILS, dispatch, get_job_spec
from lava.lib.datetime import duration_to_seconds
from lava.lib.logging import get_log_level
from lava.lib.misc import dict_check, json_default, size_to_bytes
from s3event import S3EventRecord

__author__ = 'Murray Andrews'

# If LOGNAME is set to None you get all the boto3 events as well.
LOG = logging.getLogger(name=LOGNAME)

try:
    REALM = os.environ['LAVA_REALM']
except KeyError:
    raise Exception('LAVA_REALM environment variable must be set.')

TRIGGER_TABLE = f'lava.{REALM}.s3triggers'
JOBS_TABLE = f'lava.{REALM}.jobs'

TRIGGER_REQUIRED_FIELDS = {'bucket', 'prefix', 'job_id', 'enabled', 'trigger_id'}

# This list will get augmented by decorator event_condition()
TRIGGER_OPTIONAL_FIELDS = {'globals', 'parameters', 'description', 'jinja', 'delay', 'owner'}

CONDITION_CHECKERS = {}

# Cache for hits on the s3triggers and jobs tables.
CACHE_TTL = config('S3TRIGGER_CACHE_TTL', duration_to_seconds)
S3_DEDUP_TTL = config('S3TRIGGER_DEDUP_TTL', duration_to_seconds)
S3_DEDUP_CACHE_SIZE = config('S3TRIGGER_DEDUP_CACHE_SIZE', int)

TRIGGER_CACHE = TTLCache(maxsize=200, ttl=CACHE_TTL) if CACHE_TTL > 0 else None
JOB_CACHE = TTLCache(maxsize=200, ttl=CACHE_TTL) if CACHE_TTL > 0 else None
S3_OBJECT_CACHE = (
    TTLCache(maxsize=S3_DEDUP_CACHE_SIZE, ttl=S3_DEDUP_TTL) if S3_DEDUP_CACHE_SIZE else None
)
S3_CACHE_LOCK = RLock()


# ------------------------------------------------------------------------------
def event_condition(condition_type: str) -> Callable:
    """
    Register if_* conditions.

    Usage:

        @event_condition('condition_type')
        a_func(event, condition_arg)

    This then gets used in an s3trigger entry as:

    .. code::  json

        {
            "if_condition_type": value,
            "if_not_condition_type": value
        }

    :param condition_type:  The condition type. This will be in the s3triggers
                            table entry with a prefix of ``if_`` or ``if_not_``.

    """

    def decorate(func):
        """
        Register the condition checker function and its inverse.

        :param func:    Function to register.
        :return:        Unmodified function.

        """

        if condition_type in CONDITION_CHECKERS:
            raise Exception(f'{condition_type} is already registered')
        TRIGGER_OPTIONAL_FIELDS.add(f'if_{condition_type}')
        TRIGGER_OPTIONAL_FIELDS.add(f'if_not_{condition_type}')

        # Add condition checking functions to our registry
        CONDITION_CHECKERS[f'if_{condition_type}'] = func
        # This is dodgy as we are preserving a local lambda outside local context
        CONDITION_CHECKERS[f'if_not_{condition_type}'] = lambda event, event_arg: not func(
            event, event_arg
        )
        return func

    return decorate


# ------------------------------------------------------------------------------
def setup_logging(level: str, name: str = None) -> None:
    """
    Set up logging.

    :param level:   Logging level. The string format of a level (eg 'debug').
    :param name:    Logger name. Default None implies root logger.

    """

    logger = logging.getLogger(name)
    logger.setLevel(get_log_level(level))
    logger.debug(f'Log level set to {level} ({logger.getEffectiveLevel()})')


# ------------------------------------------------------------------------------
@cached(JOB_CACHE, lock=RLock(), key=lambda job_id, _: job_id)
def cached_get_job_spec(job_id: str, jobs_table) -> dict[str, Any]:
    """
    Get the job spec from the DynamoDB table.

    This is a cached version of the base implementation.

    :param job_id:      Job ID.
    :param jobs_table:  DynamoDB jobs table resource.

    :return:            The job spec.

    """

    return get_job_spec(job_id, jobs_table)


# ------------------------------------------------------------------------------
@cached(TRIGGER_CACHE, lock=RLock(), key=lambda bkt, pfx, _: (bkt, pfx))
def query_trigger_table(bucket: str, prefix: str, trigger_table) -> list[dict[str, Any]]:
    """
    Run a query on the trigger table and return the raw results.

    Uses the global secondary index (GSI) `s3trigger-index`.

    :param bucket:          Bucket n2yyame.
    :param prefix:          Object prefix.
    :param trigger_table:   DynamoDB s3triggers table resource.

    :return:                The raw query results.

    """

    LOG.debug(f'Trigger query: s3://{bucket}/{prefix}')

    response = trigger_table.query(
        TableName=trigger_table.table_name,
        IndexName='s3trigger-index',
        KeyConditionExpression='#bucket = :bucket AND #prefix = :prefix',
        ExpressionAttributeNames={'#bucket': 'bucket', '#prefix': 'prefix'},
        ExpressionAttributeValues={':bucket': bucket, ':prefix': prefix},
    )
    LOG.debug('Found %d matches', len(response['Items']))

    if response['Items']:
        # Found a match. Because of key limitations in Dynamo there will be 1 result.
        sqs_max_delay_mins = config('SQS_MAX_DELAY_MINS', int)
        for trigger_spec in response['Items']:  # type: dict
            try:
                dict_check(
                    trigger_spec,
                    required=TRIGGER_REQUIRED_FIELDS,
                    optional=TRIGGER_OPTIONAL_FIELDS,
                    ignore=IGNORE_FIELDS,
                )
            except ValueError as e:
                raise Exception(f'Bad trigger spec for s3://{bucket}/{prefix} - {e}')
            trigger_spec.setdefault('jinja', True)
            trigger_spec.setdefault('delay', 0)
            try:
                trigger_spec['delay'] = duration_to_seconds(trigger_spec['delay'])
                if not 0 <= trigger_spec['delay'] <= sqs_max_delay_mins * 60:
                    raise ValueError(f'must be between 0 and {sqs_max_delay_mins} minutes')
            except Exception as e:
                raise Exception(f'Bad delay: {trigger_spec["delay"]}: {e}')

    return response['Items']


# ------------------------------------------------------------------------------
def get_trigger_specs(bucket: str, key: str, trigger_table) -> list[dict[str, Any]]:
    """
    Get trigger records from the s3triggers table for the given bucket/key.

    We recurse up the prefix hiearchy to find a match. Note that an empty prefix
    is not an option because of the limitations of DynamoDB. (Google NDB where
    art thou?)

    For example, if the object key is x/y/z, we search for the following entries
    in order:

        x/y/z
        x/y
        x/

    Only the entries matching at the first non-empty level are returned.

    Note that we have a TTL cache here to reduce unnecessary hits on the s3triggers
    table.

    :param bucket:          Bucket name.
    :param key:             Object key.
    :param trigger_table:   DynamoDB s3triggers table resource.

    :return:                A list mapping records.

    :raises KeyError:       If no matching record.

    """

    key_path = key.split('/')

    for n in range(len(key_path), 0, -1):
        trigger_key = '/'.join(key_path[0:n])

        results = query_trigger_table(bucket, trigger_key, trigger_table)
        if results:
            return results

    # Have not found an entry with a specific prefix ... look for a wildcard.
    # DynamoDB can't handle empty strings or None range values so use a * as a
    # sentinel value meaning look at bucket root.

    results = query_trigger_table(bucket, '*', trigger_table)
    if results:
        return results

    raise KeyError(f'No trigger entry for s3://{bucket}/{key}')


# ------------------------------------------------------------------------------
@event_condition('fnmatch')
def if_fnmatch(event: dict[str, Any], glob_pattern: str | list[str]) -> bool:
    """
    Check if the S3 object key of the given event matches the glob pattern(s).

    :param event:           A canonical representation of the event record.
                            See `S3EventRecord.canon`.
    :param glob_pattern:    A glob style pattern (as per fnmatch.fnmatch) or a
                            list of patterns.

    :return:                True if any of the patterns match.
    """

    if isinstance(glob_pattern, str):
        glob_pattern = [glob_pattern]
    elif not isinstance(glob_pattern, list):
        raise ValueError('glob patterns must be a string or list of strings')

    key = str(unquote_plus(event['key']))
    for pat in glob_pattern:
        if not isinstance(pat, str):
            raise ValueError('glob patterns must be strings')
        if fnmatch(key, pat):
            return True

    return False


# ------------------------------------------------------------------------------
@event_condition('size_gt')
def if_size_gt(event: dict[str, Any], size: str) -> bool:
    """
    Check if the S3 object size is greater than the specified size.

    :param event:           A canonical representation of the event record.
                            See `S3EventRecord.canon`.
    :param size:            A size string eg. '20K'.

    :return:                True if size is greater than specified value.

    """

    return event['size'] > size_to_bytes(size)


# ------------------------------------------------------------------------------
@event_condition('event_type')
def if_event_type(event: dict[str, Any], event_type: str) -> bool:
    """
    Check if the S3 event type matches the given glob pattens(s).

    Glob style matching is used to allow matches of the form ``ObjectCreated:Put``
    and ``ObjectCreated:*``.

    :param event:           A canonical representation of the event record.
                            See `S3EventRecord.canon`.
    :param event_type:      The S3 event type (e.g. ObjectCreated:Put)

    :return:                True if the event type matches the pattern.
    :rtype:                 bool
    """

    return fnmatch(event['event_type'], event_type)


# ------------------------------------------------------------------------------
def event_conditions_ok(trig_spec: dict[str, Any], event_rec: S3EventRecord) -> bool:
    """
    Run the event condition checkers from a trigger spec against an S3 event record.

    :param trig_spec:   The trigger spec.
    :param event_rec:   The S3 event record.
    :return:            True if the event passed the checks, False otherwise.
    """

    for condition_type, condition_arg in (
        (k, trig_spec[k]) for k in trig_spec if k.startswith('if_')
    ):
        if condition_type not in CONDITION_CHECKERS:
            raise KeyError(f'{condition_type}: Unknown condition type')

        if not CONDITION_CHECKERS[condition_type](event_rec.canon, condition_arg):
            LOG.info(
                '%s: s3://%s/%s doesn\'t satisfy %s',
                trig_spec['trigger_id'],
                event_rec.bucket,
                event_rec.key,
                condition_type,
            )
            return False

    return True


# ------------------------------------------------------------------------------
def s3_duplicate_event(rec: S3EventRecord) -> datetime | None:
    """
    Check if this bucket/key combo has occurred recently.

    Two events are considered to be duplicates if the following attributes match:

    -   bucket
    -   key
    -   event type
    -   object size.

    :param rec:         The S3 event record.
    :return:            The timestamp of a previous event if its a duplicate,
                        otherwise None.
    """

    if S3_OBJECT_CACHE is None:
        return None

    with S3_CACHE_LOCK:
        dedup_key = (rec.bucket, rec.key, rec.event_type, rec.size)
        if ts := S3_OBJECT_CACHE.get(dedup_key):
            return ts
        S3_OBJECT_CACHE[dedup_key] = rec.event_time
    return None


# ------------------------------------------------------------------------------
def lambda_handler(event: dict[str, Any], context) -> None:
    """
    AWS lambda entry point.

    :param event:       Lambda event data.
    :param context:     Lambda context. This will be populated if running in
                        lambda but None if running in an eventworker.
    :type event:        dict

    """

    setup_logging(os.environ.get('LOGLEVEL', LOGLEVEL), name=LOGNAME)
    LOG.debug('Received event: %s', json.dumps(event, sort_keys=True, indent=2))

    aws_session = boto3.Session()

    try:
        trigger_table = aws_session.resource('dynamodb').Table(TRIGGER_TABLE)
    except Exception as e:
        raise Exception(f'Cannot get DynamoDB table {TRIGGER_TABLE} - {e}')

    try:
        job_table = aws_session.resource('dynamodb').Table(JOBS_TABLE)
    except Exception as e:
        raise Exception(f'Cannot get DynamoDB table {JOBS_TABLE} - {e}')

    errors = 0

    for rec in S3EventRecord.extract_records(event):
        bucket = rec.bucket
        key = rec.key
        LOG.debug('Processing event for s3://%s/%s', bucket, key)

        if ts := s3_duplicate_event(rec):
            LOG.warning('s3://%s/%s: Duplicate event discarded (original ts=%s)', bucket, key, ts)
            continue

        try:
            trigger_specs = get_trigger_specs(bucket, key, trigger_table)
        except Exception as e:
            errors += 1
            LOG.error('s3://%s/%s: %s', bucket, key, e)
            continue

        for trig_spec in trigger_specs:
            LOG.debug('Trigger spec: %s', trig_spec)
            trigger_id = trig_spec['trigger_id']
            if not trig_spec['enabled']:
                LOG.warning('%s: s3://%s/%s: s3trigger not enabled', trigger_id, bucket, key)
                continue

            # ------------------------------------
            # Run any event condition checkers
            try:
                if not event_conditions_ok(trig_spec, rec):
                    continue
            except Exception as e:
                errors += 1
                LOG.error('%s: Event condition(s) failed: %s', trigger_id, e)
                continue

            # ------------------------------------
            # Get the list of jobs to dispatch

            job_ids = trig_spec['job_id']
            if isinstance(job_ids, str):
                job_ids = [job_ids]
            elif not isinstance(job_ids, list):
                errors += 1
                LOG.error('%s: job_id must be string or list of strings', trigger_id)
                continue

            # ------------------------------------
            # Render job globals from the trigger spec

            render_vars = {
                'bucket': bucket,
                'key': key,
                'event': rec.raw,
                'info': rec.canon,
                'utils': JINJA_UTILS,
            }

            globals_ = trig_spec.get('globals')
            if globals_ and trig_spec['jinja']:
                try:
                    globals_ = json.loads(
                        jinja2.Template(
                            json.dumps(trig_spec['globals'], indent=2, default=json_default)
                        ).render(**render_vars)
                    )
                except Exception as e:
                    errors += 1
                    LOG.error(
                        '%s: s3://%s/%s: Cannot render globals: %s', trigger_id, bucket, key, e
                    )
                    continue

                LOG.debug('Rendered job globals: %s', globals_)

            # ------------------------------------
            # Render job parameters from the trigger spec

            params = trig_spec.get('parameters')
            if params and trig_spec['jinja']:
                try:
                    params = json.loads(
                        jinja2.Template(
                            json.dumps(trig_spec['parameters'], indent=2, default=json_default)
                        ).render(**render_vars)
                    )
                except Exception as e:
                    errors += 1
                    LOG.error(
                        '%s: s3://%s/%s: Cannot render parameters: %s',
                        trigger_id,
                        bucket,
                        key,
                        e,
                    )
                    continue

                LOG.debug('Rendered job params: %s', params)

            # ------------------------------------
            # Dispatch the job(s)

            for jid in job_ids:
                if trig_spec['jinja']:
                    try:
                        jid = jinja2.Template(jid).render(**render_vars)
                    except Exception as e:
                        errors += 1
                        LOG.error(
                            '%s: s3://%s/%s: Cannot render job_id %s: %s',
                            trigger_id,
                            bucket,
                            key,
                            jid,
                            e,
                        )
                        continue

                # Get the job spec so we can determine the worker
                try:
                    job_spec = cached_get_job_spec(jid, job_table)
                except Exception as e:
                    errors += 1
                    LOG.error('%s: s3://%s/%s: %s: %s', trigger_id, bucket, key, jid, e)
                    continue

                # Skip jobs that are not enabled. Could leave this to the worker
                # but may as well do it here.
                if not job_spec['enabled']:
                    LOG.warning('%s: Job %s is not enabled', trigger_id, jid)
                    continue

                try:
                    run_id = dispatch(
                        realm=REALM,
                        job_id=jid,
                        worker=job_spec['worker'],
                        params=params,
                        delay=trig_spec['delay'],
                        globals_=globals_,
                        aws_session=aws_session,
                    )
                except Exception as e:
                    errors += 1
                    LOG.error('%s: s3://%s/%s: %s', trigger_id, bucket, key, e)
                    continue
                else:
                    LOG.info(
                        '%s: s3://%s/%s: Dispatched job %s (%s)',
                        trigger_id,
                        bucket,
                        key,
                        jid,
                        run_id,
                    )

    if errors:
        LOG.error('Event %s: Completed with %s errors', context.aws_request_id, errors)
    else:
        LOG.info('Event %s: Completed', context.aws_request_id)
