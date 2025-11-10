"""
Handle event logging.

Current implementation writes back to DynamoDB.

"""

from __future__ import annotations

import logging
import socket
import threading
from datetime import datetime, timezone
from queue import Queue
from typing import Any

import boto3

from lava.config import LOGNAME, config
from lava.lavacore import ThreadMonitor
from lava.lib.aws import ec2_instance_id
from lava.lib.datetime import duration_to_seconds, now_tz

__author__ = 'Murray Andrews'

LOG = logging.getLogger(name=LOGNAME)

_EVENT_QUEUE = Queue(maxsize=0)
_LAVA_EVENT_TTL = None


# ------------------------------------------------------------------------------
def log_event(job_spec: dict[str, Any], status: str, info: Any = None) -> datetime:
    """
    Send an event record to the event logger thread.

    :param job_spec:    Job spec.
    :param status:      The event type
    :param info:        An arbitrary blob

    :return:            A timezone aware datetime associated with the event.
    """

    # Warning -- this is non threadsafe hack but it is safe enough as it only
    # runs once. Just want to avoid doing new conversion on each log event.
    global _LAVA_EVENT_TTL
    if _LAVA_EVENT_TTL is None:
        _LAVA_EVENT_TTL = duration_to_seconds(config('EVENT_TTL')) if config('EVENT_TTL') else 0

    now = now_tz()  # Timezone aware
    # Create a naive UTC based version. This is handy for some housekeeping
    # operations on the logging database.
    now_utc = now.astimezone(timezone.utc).replace(tzinfo=None).isoformat()

    mesg = {
        'job_id': job_spec['job_id'],
        'run_id': job_spec['run_id'],
        'ts_dispatch': job_spec['ts_dispatch'],
        'status': status,
        'ts_event': now,
        'tu_event': now_utc,
        'info': info,
    }

    if _LAVA_EVENT_TTL:
        mesg['ttl'] = int(now.timestamp() + _LAVA_EVENT_TTL)

    _EVENT_QUEUE.put(mesg)

    return now


# ------------------------------------------------------------------------------
class EventRecorder(threading.Thread):
    """
    Record Lava events to an external log database.

    Current implementation writes back to DynamoDB.

    :param worker:      Name of this lava worker.
    :param profile:     AWS profile name (for credentials selection)
    :param realm_info:  A dictionary of realm wide parameters.

    """

    # --------------------------------------------------------------------------
    def __init__(
        self, worker: str, profile: str, realm_info: dict[str, Any], *args, **kwargs
    ) -> None:
        """Create an EventRecorder worker."""

        super().__init__(*args, **kwargs)

        self.worker = worker
        self.realm_info = realm_info
        self.realm = realm_info['realm']

        # noinspection PyBroadException
        try:
            self.worker_id = ec2_instance_id()
        except Exception:
            self.worker_id = None

        self.hostname = socket.gethostname()

        # noinspection PyBroadException
        try:
            self.instance_id = ec2_instance_id()
        except Exception:
            self.instance_id = None

        # Boto sessions are not thread safe so need one per thread.
        self.aws_session = boto3.Session(profile_name=profile)

        event_table_name = 'lava.' + self.realm + '.events'
        try:
            self.event_table = self.aws_session.resource('dynamodb').Table(event_table_name)
        except Exception as e:
            raise Exception(f'Cannot get DynamoDB table {event_table_name} - {e}')

    # --------------------------------------------------------------------------
    def run(self) -> None:
        """
        Loop on event records from the event queue and log them to DynamoDB.

        Records look like this:

        ```python
        {
            'job_id': ...,
            'run_id': ...,
            'ts_dispatch': datetime with TZ,
            'ts_event': datetime with TZ,
            'tu_event': naive UTC based datetime
            'status': ...,
            'info': ...,
        }
        ```

        """

        LOG.debug('Starting')
        ThreadMonitor().register_thread()

        while True:
            event_rec = _EVENT_QUEUE.get()  # type: dict

            # ----------------------------------------
            # Augment the event record
            event_rec.update(worker=self.worker, worker_id=self.worker_id, hostname=self.hostname)
            if self.instance_id:
                event_rec['instance_id'] = self.instance_id

            # ----------------------------------------
            # Adjust it for DynamoDB.

            # Need to remove the key fields from the DynamoDB update record.
            job_id = event_rec['job_id']
            run_id = event_rec['run_id']
            info = event_rec['info']

            del event_rec['job_id']
            del event_rec['run_id']
            del event_rec['info']

            # Convert datetimes to strings.
            for k, v in [(k, v) for k, v in event_rec.items() if isinstance(v, datetime)]:
                event_rec[k] = v.isoformat()

            # Convert empty string to None. DynamoDB doesn't like empty strings!
            for k in [k for k, v in event_rec.items() if not v]:
                event_rec[k] = None

            # ----------------------------------------
            # Build the DynamoDB update arguments. What an awful API design.

            expr_attr_names = {}
            expr_attr_values = {}
            update_expr = []
            for k, v in event_rec.items():
                expr_attr_names['#' + k] = k
                expr_attr_values[':' + k] = v
                update_expr.append(f'#{k} = :{k}')

            # Add a log which is a list of events for this job / run
            expr_attr_names['#log'] = 'log'
            expr_attr_values[':_empty_list'] = []
            expr_attr_values[':log'] = [
                {
                    'ts_event': event_rec['ts_event'],
                    'tu_event': event_rec['tu_event'],
                    'status': event_rec['status'],
                    'info': info,
                }
            ]
            update_expr.append('#log = list_append(if_not_exists(#log, :_empty_list), :log)')

            # ----------------------------------------
            # Do the update

            try:
                self.event_table.update_item(
                    Key={'job_id': job_id, 'run_id': run_id},
                    UpdateExpression='SET ' + ', '.join(update_expr),
                    ExpressionAttributeNames=expr_attr_names,
                    ExpressionAttributeValues=expr_attr_values,
                    ReturnValues='NONE',
                )
            except Exception as e:
                LOG.error(
                    f'Could not log to {self.event_table.name}: {e}', extra={'event_type': 'worker'}
                )
            finally:
                _EVENT_QUEUE.task_done()
