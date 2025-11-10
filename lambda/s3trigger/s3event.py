"""
Attempt to provide some basic common interface to AWS S3 events.

These vary in format depending on whether its a conventional S3 bucket
notification configuration event or the newer EventBridge event mechanism. In
the former case, the format also varies depending on whether the message was
delivered directly from S3 to AWS lambda or via SNS or SQS (all different). :-(

Requires Python3.9 runtime.
"""

from __future__ import annotations

import json
import os
from abc import ABC, abstractmethod
from collections.abc import Iterator
from datetime import datetime
from functools import cached_property
from ipaddress import IPv4Address, IPv6Address, ip_address
from typing import Any
from urllib.parse import unquote_plus

from dateutil.parser import parse

AWS_REGION = os.environ.get('AWS_REGION')


# ------------------------------------------------------------------------------
class S3EventRecord(ABC):
    """
    Base class for handlers for different formats.

    :param event_record:    The raw record.
    """

    # Attributes to return for canonical representation
    CANON = ('bucket', 'key', 'size', 'source_ip', 'event_time', 'event_type', 'aws_region')

    # --------------------------------------------------------------------------
    def __init__(self, event_record: dict[str, Any]):
        """Capture the raw record and try to get some basic attributes."""

        self.raw = event_record

    # --------------------------------------------------------------------------
    def __str__(self):
        """Stringify."""
        return str(self.raw)

    # --------------------------------------------------------------------------
    def __repr__(self):
        """Represent."""
        return str(self.raw)

    # --------------------------------------------------------------------------
    @cached_property
    def canon(self) -> dict[str, Any]:
        """Get a canonical representation of a subset of the event attributes."""

        return {attr: getattr(self, attr) for attr in self.CANON}

    # --------------------------------------------------------------------------
    @property
    @abstractmethod
    def bucket(self) -> str:
        """Get the bucket name."""
        ...

    # --------------------------------------------------------------------------
    @property
    @abstractmethod
    def key(self) -> str:
        """Get the object key."""
        ...

    # --------------------------------------------------------------------------
    @property
    @abstractmethod
    def size(self) -> int:
        """Get the object size."""
        ...

    # --------------------------------------------------------------------------
    @property
    @abstractmethod
    def source_ip(self) -> IPv4Address | IPv6Address | None:
        """Get the source IP address."""
        ...

    # --------------------------------------------------------------------------
    @property
    @abstractmethod
    def event_time(self) -> datetime:
        """Get the event time as a timezone aware datetime."""
        ...

    # --------------------------------------------------------------------------
    @property
    @abstractmethod
    def event_type(self) -> str:
        """Get the event type (eg. ObjectCreated:Put*)."""
        ...

    # --------------------------------------------------------------------------
    @property
    @abstractmethod
    def aws_region(self) -> str:
        """Get the AWS region."""
        ...

    # --------------------------------------------------------------------------
    @classmethod
    def extract_records(cls, event: dict[str, Any]) -> Iterator[S3EventRecord]:
        """
        Extract event records from an event blob received by an AWS Lambda function.

        :param event:   An event blob received by an AWS Lambda function. This
                        handles the variations depending on source.

        :return:        An iterator of S3EventRecords.
        """

        if not isinstance(event, dict):
            raise ValueError('Event blob must be a dict')

        if event.get('Event') == 's3:TestEvent':
            # These test events are really annoying - silently ignore them
            return

        if isinstance(event.get('Records'), list):
            # Try the conventional S3 bucket event notification config format first.
            for r in event['Records']:
                # SNS and SQS cannot even agree on case for event source. Aaaargh.
                event_source = r.get('eventSource', r.get('EventSource'))
                if event_source == 'aws:sqs':
                    # A nested event record structure is encapsulated in the body
                    for rec in cls.extract_records(json.loads(r['body'])):
                        yield rec
                elif event_source == 'aws:sns':
                    # A nested event record structure is encapsulated in the body but
                    # differently to SQS. Aaargh.
                    for rec in cls.extract_records(json.loads(r['Sns']['Message'])):
                        yield rec
                elif event_source == 'aws:s3':
                    # And native lambda subscription is different again.
                    yield S3BucketEventNotificationRecord(r)
                else:
                    raise ValueError(f'Unexpected event source: {event_source}')
        elif 'detail-type' in event:
            yield S3EventBridgeRecord(event)
        else:
            raise ValueError('Cannot determine event format')


# ------------------------------------------------------------------------------
class S3BucketEventNotificationRecord(S3EventRecord):
    """
    The conventional S3 bucket event notification record (e.g. via SNS, SQS).

    They look like this:

    .. code:: json

        {
          "eventVersion": "2.0",
          "eventTime": "1970-01-01T00:00:00.000Z",
          "requestParameters": {
            "sourceIPAddress": "127.0.0.1"
          },
          "s3": {
            "configurationId": "testConfigRule",
            "object": {
              "eTag": "0123456789abcdef0123456789abcdef",
              "sequencer": "0A1B2C3D4E5F678901",
              "key": "HappyFace.jpg",
              "size": 1024
            },
            "bucket": {
              "arn": "bucketarn",
              "name": "sourcebucket",
              "ownerIdentity": {
                "principalId": "EXAMPLE"
              }
            },
            "s3SchemaVersion": "1.0"
          },
          "responseElements": {
            "x-amz-id-2": "EXAMPLE123/5678abcdefghijklambdaisawesome/mnopqrstuvwxyzABCDEFGH",
            "x-amz-request-id": "EXAMPLE123456789"
          },
          "awsRegion": "us-east-1",
          "eventName": "ObjectCreated:Put",
          "userIdentity": {
            "principalId": "EXAMPLE"
          },
          "eventSource": "aws:s3"
        }
    """

    # --------------------------------------------------------------------------
    @property
    def bucket(self) -> str:
        """Get the bucket name."""
        return self.raw['s3']['bucket']['name']

    # --------------------------------------------------------------------------
    @property
    def key(self) -> str:
        """Get the object key."""
        return str(unquote_plus(self.raw['s3']['object']['key']))

    # --------------------------------------------------------------------------
    @property
    def size(self) -> int:
        """Get the object size."""

        return self.raw['s3']['object']['size']

    # --------------------------------------------------------------------------
    @property
    def source_ip(self) -> IPv4Address | IPv6Address | None:
        """Get the source IP address."""

        # noinspection PyBroadException
        try:
            return ip_address(self.raw['requestParameters']['sourceIPAddress'])
        except Exception:
            return None

    # --------------------------------------------------------------------------
    @property
    def event_time(self) -> datetime:
        """Get the event time as a timezone aware datetime."""

        return parse(self.raw['eventTime'])

    # --------------------------------------------------------------------------
    @property
    def event_type(self) -> str:
        """Get the event type (eg. ObjectCreated:Put*)."""

        return self.raw['eventName']

    # --------------------------------------------------------------------------
    @property
    def aws_region(self) -> str:
        """Get the AWS region."""

        return self.raw.get('awsRegion', AWS_REGION)


# ------------------------------------------------------------------------------
class S3EventBridgeRecord(S3EventRecord):
    """
    The newer event record format S3 sends to Event Bridge.

    They look like this:

    .. code:: json

        {
            "version": "0",
            "id": "1e22c59c-015a-cd36-cca9-1b65e749706f",
            "detail-type": "Object Created",
            "source": "aws.s3",
            "account": "258928625002",
            "time": "2022-01-22T05:16:19Z",
            "region": "ap-southeast-2",
            "resources": [
                "arn:aws:s3:::mybucket"
            ],
            "detail": {
                "version": "0",
                "bucket": {
                    "name": "mybucket"
                },
                "object": {
                    "key": "myfile",
                    "size": 10445,
                    "etag": "61484bb79d52a00fbdadfd61c230d6f9",
                    "sequencer": "0061EB9323D941BCDB"
                },
                "request-id": "ZPJXPT6X0AK24FCQ",
                "requester": "258928625002",
                "source-ip-address": "121.183.34.120",
                "reason": "PutObject"
            }
        }

    """

    # --------------------------------------------------------------------------
    @property
    def bucket(self) -> str:
        """Get the bucket name."""

        return self.raw['detail']['bucket']['name']

    # --------------------------------------------------------------------------
    @property
    def key(self) -> str:
        """Get the object key."""

        return self.raw['detail']['object']['key']

    # --------------------------------------------------------------------------
    @property
    def size(self) -> int:
        """Get the object size."""

        return self.raw['detail']['object']['size']

    # --------------------------------------------------------------------------
    @property
    def source_ip(self) -> IPv4Address | IPv6Address | None:
        """Get the source IP address."""

        # noinspection PyBroadException
        try:
            return ip_address(self.raw['detail']['source-ip-address'])
        except Exception:
            return None

    # --------------------------------------------------------------------------
    @property
    def event_time(self) -> datetime:
        """Get the event time as a timezone aware datetime."""

        return parse(self.raw['time'])

    # --------------------------------------------------------------------------
    @property
    def event_type(self) -> str:
        """
        Get the event type (eg. ObjectCreated:Put*).

        .. warning::
            These can vary subtly from the normal S3 events (e.g.
            `ObjectCreated:Put` vs `ObjectCreated:PutRecord`) but the bit before
            the colon should be pretty consistent.
        """

        return ':'.join([self.raw['detail-type'], self.raw['detail']['reason']]).replace(' ', '')

    # --------------------------------------------------------------------------
    @property
    def aws_region(self) -> str:
        """Get the AWS region."""

        return self.raw.get('region', AWS_REGION)
