"""
Handle post job actions.

A lot of this is pre-existing code from rsDropLoader2.

"""

from __future__ import annotations

import json
import logging
from contextlib import suppress
from typing import Any

import boto3
import jinja2
from botocore.client import Config
from dateutil.tz import UTC

from lava.config import config
from lava.connection import get_email_connection, get_slack_connection
from lava.lib.aws import ses_send
from lava.lib.datetime import duration_to_seconds
from lava.lib.misc import dict_check, json_default
from lava.lib.state import LavaStateItem
from .lavacore import LOGNAME, LavaError, dispatch, jinja_render_vars

__author__ = 'Murray Andrews'

LOG = logging.getLogger(name=LOGNAME)

ACTION_HANDLERS = {}

ACTION_REQUIRED_FIELDS = {'action'}
SNS_MAX_SUBJECT_LEN = 100  # Imposed by AWS SNS API


# ------------------------------------------------------------------------------
def action(*args):
    """
    Register action handlers.

    Usage:

    ```python
    @action('action_type1', ...)
    a_func(...)
    ```

    :param args:        A list of action types that the decorated function
                        handles.
    :type args:         str
    """

    def decorate(func):
        """
        Register the handler function.

        :param func:    Function to register.
        :return:        Unmodified function.

        """
        for action_type in args:
            if action_type in ACTION_HANDLERS:
                raise Exception(f'{action_type}  is already registered')
            ACTION_HANDLERS[action_type] = func
        return func

    return decorate


# ------------------------------------------------------------------------------
@action('dispatch')
def action_dispatch(
    action_info: dict[str, Any],
    job_spec: dict[str, Any],
    realm_info: dict[str, Any],
    job_result: dict[str, Any],
    aws_session: boto3.Session = None,
) -> None:
    """
    Send an SQS message to dispatch another job.

    The other job must be in the same realm.

    The action_info keys are:

    - job_id
        The other job ID. Required.

    - parameters
        An optional dictionary of parameters that will be sent with the
        dispatch. It is rendered using Jinja2 with the job spec, realm info and
        job result data being injected.

    - delay
        An optional duration string specifying a delay in the dispatch message.
        Must be <=15 min

    :param action_info:     A dictionary of parameters for this action.
    :param job_spec:        The job spec.
    :param realm_info:      The realm info.
    :param job_result:      The result dictionary from the job run.
    :param aws_session:     A boto3 Session object.

    """

    # ----------------------------------------
    def render(s: str) -> str:
        """Jinja render a string."""
        return jinja2.Template(s).render(**render_vars)

    # ----------------------------------------
    dict_check(action_info, required=({'job_id'}))
    render_vars = jinja_render_vars(job_spec, realm_info, result=job_result)

    max_delay_mins = config('SQS_MAX_DELAY_MINS', int)
    delay = action_info.get('delay', 0)

    try:
        delay = int(duration_to_seconds(delay))
        if not 0 <= delay <= max_delay_mins * 60:
            raise ValueError(f'Must be between 0 and {max_delay_mins} minutes')
    except Exception as e:
        raise LavaError(f'Bad delay: {delay}: {e}')

    params = None

    if action_info.get('parameters'):
        # Render parameters. This is a bit of a hack wehere we JSON serialise,
        # render then deserialise.
        try:
            params = json.loads(
                render(json.dumps(action_info['parameters'], indent=2, default=json_default))
            )
        except Exception as e:
            raise LavaError(f'Cannot render parameters - {e}')

    try:
        target_job_id = render(action_info['job_id'])
    except Exception as e:
        raise LavaError(f'Cannot render target job_id - {e}')

    # ------------------------------
    # Prepare globals for the child.
    # Set the current job as the parent. Master job will already be set

    child_globals: dict[str, Any] = dict(job_spec['globals'])
    lava_globals = child_globals['lava']
    lava_globals['parent_job_id'] = job_spec['job_id']
    lava_globals['parent_start'] = job_spec['ts_start'].isoformat()
    lava_globals['parent_ustart'] = job_spec['ts_start'].astimezone(UTC).isoformat()

    # ------------------------------
    dispatch(
        realm=realm_info['realm'],
        job_id=target_job_id,
        params=params,
        globals_=job_spec['globals'],
        delay=delay,
        aws_session=aws_session,
    )


# ------------------------------------------------------------------------------
@action('sqs')
def action_sqs(
    action_info: dict[str, Any],
    job_spec: dict[str, Any],
    realm_info: dict[str, Any],
    job_result: dict[str, Any],
    aws_session: boto3.Session = None,
) -> None:
    """
    Send an SQS message.

    The supported keys are:

    - queue
        The name or URL for the queue.

    - message
        Either a string or an object that will be JSON encoded and sent as the
        SQS message. It is rendered using Jinja2 with the job spec, realm info
        and job result data being injected.

    - delay
        An optional duration string specifying a delay in the dispatch message.
        Must be <=15 min

    - dedup_id
        The token used for deduplication of sent messages. This parameter
        applies only to FIFO queues. This parameter applies only to FIFO
        (first-in-first-out) queues.

    - group_id
        The tag that specifies that a message belongs to a specific message
        group. This parameter applies only to FIFO (first-in-first-out) queues.

    :param action_info:     A dictionary of parameters for this action.
    :param job_spec:        The job spec.
    :param realm_info:      The realm info.
    :param job_result:      The result dictionary from the job run.
    :param aws_session:     A boto3 Session object. If not specified a default is
                            created.

    """

    # ----------------------------------------
    def render(s: str) -> str:
        """Jinja render a string."""
        return jinja2.Template(s).render(**render_vars)

    # ----------------------------------------
    dict_check(action_info, required=('queue', 'message'))
    render_vars = jinja_render_vars(job_spec, realm_info, result=job_result)

    if not aws_session:
        aws_session = boto3.Session()

    if '.amazonaws.com/' in action_info['queue']:
        # Assume its a URL
        sqs_queue = aws_session.resource('sqs').Queue('https://' + action_info['queue'])
    else:
        sqs_queue = aws_session.resource('sqs').get_queue_by_name(QueueName=(action_info['queue']))

    max_delay_mins = config('SQS_MAX_DELAY_MINS', int)
    delay = action_info.get('delay', 0)

    try:
        delay = int(duration_to_seconds(delay))
        if not 0 <= delay <= max_delay_mins * 60:
            raise ValueError(f'Must be between 0 and {max_delay_mins} minutes')
    except Exception as e:
        raise LavaError(f'Bad delay: {delay}: {e}')

    message = (
        action_info['message']
        if isinstance(action_info['message'], str)
        else json.dumps(action_info['message'], default=json_default)
    )

    # Check for deduplication args - FIFO queues only
    dedup_args = {}
    if sqs_queue.attributes['QueueArn'].endswith('.fifo'):
        if action_info.get('dedup_id'):
            dedup_args['MessageDeduplicationId'] = render(action_info['dedup_id'])
        if action_info.get('group_id'):
            dedup_args['MessageGroupId'] = render(action_info['group_id'])

    sqs_queue.send_message(MessageBody=render(message), DelaySeconds=delay, **dedup_args)


# ------------------------------------------------------------------------------
@action('sns')
def action_sns(
    action_info: dict[str, Any],
    job_spec: dict[str, Any],
    realm_info: dict[str, Any],
    job_result: dict[str, Any],
    aws_session: boto3.Session = None,
) -> None:
    """
    Send an SNS message.

    The required keys are:

    - topic
        The topic ARN.

    - message
        Either a string or an object that will be JSON encoded and sent as the
        SNS message. It is rendered using Jinja2 with the job spec, realm info
        and job result data being injected.

    Optional keys:

    - subject
        Message subject string. It is rendered using Jinja2 with the control
        object being injected.

    :param action_info:     A dictionary of parameters for this action.
    :param job_spec:        The job spec.
    :param realm_info:      The realm info.
    :param job_result:      The result dictionary from the job run.
    :param aws_session:     A boto3 Session object. If not specified a default is
                            created.

    """

    # ----------------------------------------
    def render(s: str) -> str:
        """Jinja render a string."""
        return jinja2.Template(s).render(**render_vars)

    # ----------------------------------------
    dict_check(action_info, required=('topic', 'message'))
    render_vars = jinja_render_vars(job_spec, realm_info, result=job_result)

    if not aws_session:
        aws_session = boto3.Session()

    sns = aws_session.client('sns', config=Config(signature_version='s3v4'))

    message = (
        action_info['message']
        if isinstance(action_info['message'], str)
        else json.dumps(action_info['message'], default=json_default)
    )

    args = {
        'TopicArn': action_info['topic'],
        'Message': render(message),
    }

    with suppress(KeyError):
        args['Subject'] = render(action_info['subject'])[:SNS_MAX_SUBJECT_LEN]

    sns.publish(**args)


# ------------------------------------------------------------------------------
# noinspection PyUnusedLocal
@action('log')
def action_log(
    action_info: dict[str, Any],
    job_spec: dict[str, Any],
    realm_info: dict[str, Any],
    job_result: dict[str, Any],
    aws_session: boto3.Session = None,
) -> None:
    """
    Write a log message at level info.

    The required keys are:

    - message
        A string. It is rendered using Jinja2 with the job spec, realm info and
        job result data being injected.

    :param action_info:     A dictionary of parameters for this action.
    :param job_spec:        The job spec.
    :param realm_info:      The realm info.
    :param job_result:      The result dictionary from the job run.
    :param aws_session:     A boto3 Session object. If not specified a default is
                            created.

    """

    dict_check(action_info, required={'message'})

    if not isinstance(action_info['message'], str):
        raise ValueError('message must be a string')

    render_vars = jinja_render_vars(job_spec, realm_info, result=job_result)
    LOG.info(
        jinja2.Template(action_info['message']).render(**render_vars),
        extra={'event_type': 'job', 'job_id': job_spec['job_id'], 'run_id': job_spec['run_id']},
    )


# ------------------------------------------------------------------------------
@action('email')
def action_email(
    action_info: dict[str, Any],
    job_spec: dict[str, Any],
    realm_info: dict[str, Any],
    job_result: dict[str, Any],
    aws_session: boto3.Session = None,
) -> None:
    """
    Send an email.

    The supported keys are:

    - from
        An optional sending email address. If bare metal SES is being used, this
        must be an SES verified email address or be in a verified domain. If not
        specified, lava will attempt to find a verified domain and use a realm
        specific user ID.

    - to
        The recipient email address. Required.

    - subject
        Message subject. It is rendered using Jinja2 with the job spec,

    - message
        Message body. It is rendered using Jinja2 with the job spec, realm info
        and job result data being injected. If it starts with <HTML> it will be
        treated as a HTML body rather than a text body.

    - attachments
        A list of file names (local or S3) that are attached to the email.

    - region
        An optional AWS region supporting SES. If not specified, us-east-1 is
        used. Only used if bare metal SES.

    - email_conn
        An optional email connector ID. If specified, this connector will be
        used to send the email. If not, then bare metal AWS SES will be used.

    :param action_info:     A dictionary of parameters for this action.
    :param job_spec:        The job spec.
    :param realm_info:      The realm info.
    :param job_result:      The result dictionary from the job run.
    :param aws_session:     A boto3 Session object. If not specified a default is
                            created.

    """

    # ----------------------------------------
    def render(s: str) -> str:
        """Jinja render a string."""
        return jinja2.Template(s).render(**render_vars)

    # ----------------------------------------
    dict_check(
        action_info,
        required=('action', 'to', 'subject', 'message'),
        optional=('from', 'region', 'email_conn', 'attachments'),
    )

    render_vars = jinja_render_vars(job_spec, realm_info, result=job_result)

    if not aws_session:
        aws_session = boto3.Session()

    subject = render(action_info['subject'])
    message = render(action_info['message'])

    # ----------------------------------------
    # See if an email connector is specified

    if action_info.get('email_conn'):
        email_conn = get_email_connection(
            conn_id=action_info['email_conn'], realm=realm_info['realm'], aws_session=aws_session
        )
        email_conn.send(
            subject=subject,
            message=message,
            to=action_info['to'],
            sender=action_info.get('from'),
            attachments=(render(a) for a in action_info.get('attachments', [])),
        )
        return

    if action_info.get('attachments'):
        raise LavaError('email_conn must be specified to enable attachments')

    # ----------------------------------------
    # No email connector -- use bare metal SES.

    # Look for SES region name in the action_info then the realm_info then use default.
    region = action_info.get('region', config('SES_REGION'))

    # Look for SES sender address in the action_info then the realm_info.
    sender = action_info.get('from', config('SES_FROM'))

    if not sender:
        # Try to guess a valid sender based on verified domains.
        ses = aws_session.client('ses', region_name=region)
        identities = ses.list_identities(IdentityType='Domain')['Identities']
        if not identities:
            raise LavaError('No verified SES domains')

        sender = f'lava.{job_spec["realm"]}@{identities[0]}'

    # Check if we are sending text or HTML
    body = {'html': message} if message[0:6].upper() == '<HTML>' else {'message': message}

    ses_send(
        sender=sender,
        to=action_info['to'],
        subject=subject,
        region=region,
        aws_session=aws_session,
        **body,
    )


# ------------------------------------------------------------------------------
@action('slack')
def action_slack(
    action_info: dict[str, Any],
    job_spec: dict[str, Any],
    realm_info: dict[str, Any],
    job_result: dict[str, Any],
    aws_session: boto3.Session = None,
) -> None:
    """
    Send a Slack message.

    - slack_conn
        Connection ID for a slack connector. Required.

    - from
        Optional sender identifier. If not specified, any default value in
        the connector is used. The value is Jinja rendered.

    - subject
        Optional message subject. The value is Jinja rendered.

    - message
        Message body. The value is Jinja rendered. Only the first 3,000
        characters are used.

    - style
        Display style for the Slack message. Options are `block` (default),
        `attachment` and `plain`.

    - colour
        Colour for the sidebar for Slack messages sent using 'attachment' style.
        This can be any hex colour code or one of the Slack special values
        `good`, `warning` or `danger`.

    - preamble
        Preamble at the start of the message. Useful values include things such
        as <!here> and <!channel> which will cause Slack to insert @here and
        @channel alert tags respectively.

    :param action_info:     A dictionary of parameters for this action.
    :param job_spec:        The job spec.
    :param realm_info:      The realm info.
    :param job_result:      The result dictionary from the job run.
    :param aws_session:     A boto3 Session object. If not specified a default is
                            created.
    """

    # ----------------------------------------
    def render(s: str) -> str:
        """Jinja render a string."""
        return jinja2.Template(s).render(**render_vars)

    # ----------------------------------------
    dict_check(
        action_info,
        required=('action', 'slack_conn', 'message'),
        optional=('from', 'subject', 'colour', 'style', 'preamble'),
    )

    render_vars = jinja_render_vars(job_spec, realm_info, result=job_result)

    if not aws_session:
        aws_session = boto3.Session()

    sender = render(action_info['from']) if 'from' in action_info else None
    subject = render(action_info['subject']) if 'subject' in action_info else None
    message = render(action_info['message'])

    slack_conn = get_slack_connection(
        conn_id=action_info['slack_conn'], realm=realm_info['realm'], aws_session=aws_session
    )

    slack_conn.send(
        message=message,
        subject=subject,
        preamble=action_info.get('preamble'),
        sender=sender,
        style=action_info.get('style'),
        colour=action_info.get('colour'),
    )


# ------------------------------------------------------------------------------
@action('event')
def action_aws_event(
    action_info: dict[str, Any],
    job_spec: dict[str, Any],
    realm_info: dict[str, Any],
    job_result: dict[str, Any],
    aws_session: boto3.Session = None,
) -> None:
    """
    Send an event to AWS EventBridge.

    The supported keys are:

    - source
        An optional source specifier. If not specified, the default is
        `lava.<REALM>`

    - resources
        An optional list of resources. If not specified, the default is empty.

    - detail_type
        An optional detail type. If not specified, the default is `Lava Job Action`.

    - detail
        An optional string or map of strings. Default is a map containing realm,
        worker. job_id, run_id and exit_status.

    - event_bus
        An optional event bus name. Defaults to the default bus.


    :param action_info:     A dictionary of parameters for this action.
    :param job_spec:        The job spec.
    :param realm_info:      The realm info.
    :param job_result:      The result dictionary from the job run.
    :param aws_session:     A boto3 Session object. If not specified a default is
                            created.
    """

    # ----------------------------------------
    def render(s: str) -> str:
        """Jinja render a string."""
        return jinja2.Template(s).render(**render_vars)

    # ----------------------------------------
    dict_check(
        action_info,
        required=('action',),
        optional=('detail', 'source', 'resources', 'detail_type', 'event_bus'),
    )

    render_vars = jinja_render_vars(job_spec, realm_info, result=job_result)

    if 'detail' in action_info:
        if isinstance(action_info['detail'], dict):
            detail = {k: render(v) for k, v in action_info['detail'].items()}
        elif isinstance(action_info['detail'], str):
            detail = render(action_info['detail'])
        else:
            raise LavaError('detail must be a string or map of strings')
    else:
        detail = {
            'realm': realm_info['realm'],
            'worker': job_spec['worker'],
            'job_id': job_spec['job_id'],
            'run_id': job_spec['run_id'],
            'exit_status': job_result['exit_status'],
        }

    if not aws_session:
        aws_session = boto3.Session()

    event_info = {
        'Source': f'lava.{realm_info["realm"]}',
        'DetailType': 'Lava Job Action',
        'Detail': json.dumps(detail, default=json_default),
    }

    if 'source' in action_info:
        event_info['Source'] = render(action_info['source'])
    if 'detail_type' in action_info:
        event_info['DetailType'] = render(action_info['detail_type'])
    if 'event_bus' in action_info:
        event_info['EventBusName'] = render(action_info['event_bus'])
    if 'resources' in action_info:
        if not isinstance(action_info['resources'], list):
            raise LavaError('resources must be a list')
        event_info['Resources'] = [render(r) for r in action_info['resources']]

    response = aws_session.client('events').put_events(Entries=[event_info])
    if response.get('FailedEntryCount', 0) > 0:
        raise LavaError(
            'Failed to put event to EventBridge: {ErrorCode}: {ErrorMessage}'.format(
                **response['Entries'][0]
            )
        )


# ------------------------------------------------------------------------------
@action('state')
def action_state_set(
    action_info: dict[str, Any],
    job_spec: dict[str, Any],
    realm_info: dict[str, Any],
    job_result: dict[str, Any],
    aws_session: boto3.Session = None,
) -> None:
    """
    Set a lava state item.

    The supported keys are:

    - state_id
        The state item ID. Required.

    - type:
        Optional state storage type. Defaults to whatever the state manager does.

    - ttl
        Optional time to live for the state item. Can be a value in seconds or a
        duration (e.g. '2h'). If greater than the maximum specified for the
        realm it will be silently reduced to that value.

    - value:
        Value of the state item. Must be JSON encodeable.

    - publisher:
        Arbitrary identifier for the publishing entity. The default is the job
        ID.

    :param action_info:     A dictionary of parameters for this action.
    :param job_spec:        The job spec.
    :param realm_info:      The realm info.
    :param job_result:      The result dictionary from the job run.
    :param aws_session:     A boto3 Session object. If not specified a default is
                            created.
    """

    # ----------------------------------------
    def render(s: str) -> str:
        """Jinja render a string."""
        return jinja2.Template(s).render(**render_vars)

    # ----------------------------------------
    dict_check(
        action_info,
        required=('action', 'state_id', 'value'),
        optional=('type', 'ttl', 'publisher', 'kms_key'),
    )

    render_vars = jinja_render_vars(job_spec, realm_info, result=job_result)

    try:
        state_id = render(action_info['state_id'])
    except Exception as e:
        raise LavaError(f'Bad state_id: {e}')

    if state_id.lower().startswith('lava'):
        raise LavaError('Bad state_id: Values beginning with "lava" are reserved')

    try:
        publisher = render(action_info.get('publisher', '{{ job.job_id }}'))
    except Exception as e:
        raise LavaError(f'Bad publisher: {e}')

    # This is a hack to Jinja render a more or less arbitrary object. It's a
    # bit wasteful unfortunately.
    try:
        value = json.loads(render(json.dumps(action_info['value'], indent=1)))
    except Exception as e:
        raise LavaError(f'Bad value: {e}')

    state = LavaStateItem.new(
        state_id=state_id,
        realm=realm_info['realm'],
        value=value,
        state_type=action_info.get('type'),
        ttl=action_info.get('ttl'),
        publisher=publisher,
        aws_session=aws_session,
        kms_key=action_info.get('kms_key'),
    )  # type: LavaStateItem
    state.put()


# ------------------------------------------------------------------------------
def do_actions(
    action_key: str,
    job_spec: dict[str, Any],
    realm_info: dict[str, Any],
    job_result: dict[str, Any] = None,
    aws_session: boto3.Session = None,
) -> None:
    """
    Run any post job actions.

    :param action_key:      The key in the job spec containing the list of
                            actions. Either 'on_fail', 'on_retry' or
                            'on_success'. If the action key is not present in
                            the job spec then the value from the realm info is
                            used.
    :param job_spec:        The job spec.
    :param realm_info:      The realm info.
    :param job_result:      The result dictionary from the job run.
    :param aws_session:     A boto3.Session() object. If not provided, a default
                            session is created.

    :raise LavaError:   If an action fails.
    """

    if not aws_session:
        aws_session = boto3.Session()

    if job_result is None:
        job_result = {}

    action_list = job_spec.get(action_key, realm_info.get(action_key, []))

    if not isinstance(action_list, list):
        raise ValueError(f'{action_key}: action must be a list')

    for a in action_list:
        # Validate the action
        try:
            dict_check(a, required=ACTION_REQUIRED_FIELDS)
        except ValueError as e:
            raise LavaError(f'{action_key} action: {e}')

        # Find a handler for the action
        action_type = a['action']
        try:
            action_handler = ACTION_HANDLERS[action_type]
        except KeyError:
            raise LavaError(f'{action_key} action: {action_type}: unknown action')

        # Run the action handler
        LOG.debug('do_actions: %s: %s', action_key, action_type)
        try:
            action_handler(a, job_spec, realm_info, job_result, aws_session=aws_session)
        except Exception as e:
            raise LavaError(f'{action_key} action: {action_type}: {e}')
