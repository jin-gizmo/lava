"""
Lambda function to assist with dispatching.

Handles some of the fiddly aspects of the dispatch process. Messages can be
received from either SNS or SQS.

The message body needs to be either:

*   One or more lines in the following format:

        job_id [ -p|--param name=value ... ] [ -g|--global name=value ... ]

    Empty lines and lines beginning with # are ignored.

*   JSON containing job_id, globals (optional), parameters (optional),
    delay (optional) keys.
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import shlex
from collections.abc import Iterable
from contextlib import suppress
from typing import Any

from lava.config import LOGLEVEL, LOGNAME, config
from lava.lavacore import IGNORE_FIELDS, dispatch
from lava.lib.argparse import StoreNameValuePair
from lava.lib.datetime import duration_to_seconds
from lava.lib.logging import get_log_level
from lava.lib.misc import dict_check, dict_expand_keys

__author__ = 'Murray Andrews'

# If LOGNAME is set to None you get all the boto3 events as well.
LOG = logging.getLogger(name=LOGNAME)

try:
    REALM = os.environ['LAVA_REALM']
except KeyError:
    raise Exception('LAVA_REALM environment variable must be set.')

PROG = 'dispatch'

DISPATCH_REQUIRED_KEYS = {'job_id'}
DISPATCH_OPTIONAL_KEYS = {'delay', 'globals', 'parameters'}


# ------------------------------------------------------------------------------
def setup_logging(level: str, name: str = None) -> None:
    """
    Set up logging.

    :param level:   Logging level. The string format of a level (eg 'debug').
    :param name:    Logger name. Default None implies root logger.

    """

    logger = logging.getLogger(name)
    logger.setLevel(get_log_level(level))
    logger.debug('Log level set to %s (%d)', level, logger.getEffectiveLevel())


# ------------------------------------------------------------------------------
def process_txt_body(msg_body: str) -> None:
    """
    Process a text formatted message body.

    Message body is one or more lines of the form:

    ..code:: python

        job_id [-d|--delay duration] [ -p|--param name=value ... ] [ -g|--global name=value ... ]

    Comment lines and empty lines are ignored.

    :param msg_body:    Text message body from the incoming event source.
    """

    for line in msg_body.splitlines():
        # --------------------------
        # Parse the dispatch line into job_id + params
        l_terms = shlex.split(line, comments=True)
        if not l_terms:
            continue

        LOG.info('Dispatch request: %s', l_terms)
        job_id = l_terms[0]

        job_args = process_job_args(l_terms[1:])

        try:
            run_id = dispatch(
                realm=REALM,
                job_id=job_id,
                params=job_args.param,
                globals_=job_args.globals,
                delay=job_args.delay,
            )
        except Exception as e:
            raise Exception(f'{job_id}@{REALM}: {e}')

        LOG.info('Dispatched %s with run_id %s', job_id, run_id)


# ------------------------------------------------------------------------------
def process_json_body(msg_obj: list | dict) -> None:
    """
    Process a JSON formatted body.

    Message body is a dict, or list of dicts in this form.

    ..code:: json

        {
          "job_id": "...",
          "delay": "DURATION",
          "globals": {"g1": "gv1"},
          "parameters": {"p1": "pv1"}
        }

    :param msg_obj:    A JSON formatted message body.

    """

    if isinstance(msg_obj, dict):
        msg_obj = [msg_obj]
    elif not isinstance(msg_obj, list):
        raise ValueError('JSON message body must be list or dict')

    for dispatch_request in msg_obj:
        if not isinstance(dispatch_request, dict):
            raise ValueError(f'{dispatch_request}: must be a dict')

        LOG.info('Dispatch request: %s', dispatch_request)

        dict_check(
            dispatch_request,
            required=DISPATCH_REQUIRED_KEYS,
            optional=DISPATCH_OPTIONAL_KEYS,
            ignore=IGNORE_FIELDS,
        )

        job_id = dispatch_request['job_id']
        try:
            run_id = dispatch(
                realm=REALM,
                job_id=job_id,
                params=dispatch_request.get('parameters'),
                globals_=dispatch_request.get('globals'),
                delay=int(duration_to_seconds(dispatch_request.get('delay', 0))),
            )
        except Exception as e:
            raise Exception(f'{job_id}@{REALM}: {e}')

        LOG.info('Dispatched %s with run_id %s', job_id, run_id)


# ------------------------------------------------------------------------------
def process_job_args(args: list[str]) -> argparse.Namespace:
    """
    Process the dispatch request args.

    :param args:        A list of arguments for the dispatch request.
    :type args:         list[str]
    :return:            The args namespace.

    """

    argp = argparse.ArgumentParser(prog=PROG, add_help=False, description='Lava dispatch helper')

    argp.add_argument('-d', '--delay', action='store', default=0)

    argp.add_argument(
        '-g', '--global', dest='globals', action=StoreNameValuePair, metavar='name=value'
    )
    argp.add_argument('-p', '--param', action=StoreNameValuePair, metavar='name=value')

    try:
        args = argp.parse_args(args)
    except SystemExit as e:
        # Catch unhelpful error exit behaviour from argparse
        raise Exception(str(e))

    # Look for any globals with names like x.y and turn this into sub-dict x[y]
    if args.globals:
        try:
            args.globals = dict_expand_keys(args.globals)
        except ValueError as e:
            raise Exception(f'Bad -g, --global args: {e}')

    # Look for any params with names like x.y and turn this into sub-dict x[y]
    if args.param:
        try:
            args.param = dict_expand_keys(args.param)
        except ValueError as e:
            raise Exception(f'Bad -p, --param args: {e}')

    try:
        d = round(duration_to_seconds(args.delay))
        if not 0 <= d <= 60 * config('SQS_MAX_DELAY_MINS', int):
            raise ValueError(f'Must be between 0 and {config("SQS_MAX_DELAY_MINS", int)} minutes')
        args.delay = d
    except ValueError as e:
        raise ValueError(f'Bad -d, --delay value: {e}')

    return args


# ------------------------------------------------------------------------------
def get_message_bodies(event: dict[str, Any]) -> Iterable[str | dict]:
    """
    Extract message bodies from the event received by the lambda.

    This handles the following formats:

    1.  SNS messages
    2.  SQS messages
    3.  "Raw" JSON.

    If the event body does not contain the "Records" key, it is assumed to be a
    "raw" event dict containing a job_id to dispatch. This handles direct lambda
    invocations and EventBridge messaages.

    Sample SNS event ...

    .. code:: json

        {
          "Records": [
            {
              "EventSource": "aws:sns",
              "EventVersion": "1.0",
              "EventSubscriptionArn": "arn:aws:sns:ap-southeast-2:{{accountId}}:ExampleTopic",
              "Sns": {
                "Type": "Notification",
                "MessageId": "95df01b4-ee98-5cb9-9903-4c221d41eb5e",
                "TopicArn": "arn:aws:sns:ap-southeast-2:123456789012:ExampleTopic",
                "Subject": "example subject",
                "Message": "example message",
                "Timestamp": "1970-01-01T00:00:00.000Z",
                "SignatureVersion": "1",
                "Signature": "EXAMPLE",
                "SigningCertUrl": "EXAMPLE",
                "UnsubscribeUrl": "EXAMPLE",
                "MessageAttributes": {
                  "Test": {
                    "Type": "String",
                    "Value": "TestString"
                  },
                  "TestBinary": {
                    "Type": "Binary",
                    "Value": "TestBinary"
                  }
                }
              }
            }
          ]
        }

    Sample SQS event ...

    .. code:: json

        {
          "Records": [
            {
              "messageId": "19dd0b57-b21e-4ac1-bd88-01bbb068cb78",
              "receiptHandle": "MessageReceiptHandle",
              "body": "Hello from SQS!",
              "attributes": {
                "ApproximateReceiveCount": "1",
                "SentTimestamp": "1523232000000",
                "SenderId": "123456789012",
                "ApproximateFirstReceiveTimestamp": "1523232000001"
              },
              "messageAttributes": {},
              "md5OfBody": "7b270e59b47ff90a553787216d55d91d",
              "eventSource": "aws:sqs",
              "eventSourceARN": "arn:aws:sqs:ap-southeast-2:123456789012:MyQueue",
              "awsRegion": "ap-southeast-2"
            }
          ]
        }

    Sample "Raw" event ...

    ..code:: json

        {
            "job_id": "...",
            "globals": { },
            "parameters": { },
            "delay": "1m"
        }

    :param event:   Lambda event data.
    :return:        An iterable of message body strings or "raw" dispatch
                    requests.
    """

    if isinstance(event.get('Records'), list):
        for rec in event['Records']:
            # SQS and SNS can't even agree on capitalisation of EventSource
            event_source = rec.get('EventSource', rec.get('eventSource'))
            if rec.get('EventSource') == 'aws:sns':
                yield rec['Sns']['Message']
            elif event_source == 'aws:sqs':
                yield rec['body']
            else:
                raise Exception(f'Event source {event_source} not supported')
    elif isinstance(event, dict) and 'job_id' in event:
        # "Raw" event
        yield event
    else:
        raise ValueError(f'Cannot determine event format: {event}')


# ------------------------------------------------------------------------------
def lambda_handler(event: dict[str, Any], context) -> None:
    """
    AWS lambda entry point.

    :param event:       Lambda event data.
    :param context:     Lambda context.

    """

    setup_logging(os.environ.get('LOGLEVEL', LOGLEVEL), name=LOGNAME)
    LOG.debug('Received event:\n%s', json.dumps(event, sort_keys=True, indent=2))

    errors = 0

    for msg_body in get_message_bodies(event):
        LOG.debug('Message body: %s', msg_body)

        # See if we have JSON or command line format.
        # noinspection PyUnusedLocal
        msg_obj = None
        with suppress(Exception):
            msg_obj = json.loads(msg_body) if isinstance(msg_body, str) else msg_body

        try:
            if msg_obj:
                process_json_body(msg_obj)
            else:
                process_txt_body(msg_body)
        except Exception as e:
            errors += 1
            LOG.error(str(e))

    if errors:
        LOG.error('Event %s: Completed with %d errors', context.aws_request_id, errors)
    else:
        LOG.info('Event %s: Completed', context.aws_request_id)
