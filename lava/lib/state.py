"""Lava state manager API."""

from __future__ import annotations

import json
import logging
from datetime import datetime
from typing import Any, Callable, TypeVar

import boto3
from boto3.dynamodb.types import Binary
from dateutil.parser import parse

from lava.config import LOGNAME, config, config_load
from lava.lavacore import LavaError
from lava.lib.datetime import duration_to_seconds, now_tz
from lava.lib.misc import dict_check, json_default

LOG = logging.getLogger(name=LOGNAME)

_STATE_HANDLERS = {}
LavaStateItemType = TypeVar('LavaStateItemType', bound='LavaStateItem')

STATE_REQUIRED_FIELDS = {'state_id', 'type', 'value', 'timestamp', 'ttl'}
STATE_OPTIONAL_FIELDS = ('publisher',)
STATE_DEFAULT_TYPE = 'json'

TTL = config('STATE_TTL', duration_to_seconds)


# ------------------------------------------------------------------------------
def state_types() -> list[str]:
    """Return a list of available state item types."""
    return sorted(_STATE_HANDLERS.keys())


# ------------------------------------------------------------------------------
def state(*args: str) -> Callable:
    """
    Register handler classes for different state types.

    Usage:

        @state_type(type1, ...)
        a_class(...)

    :param args:        A list of state types that the decorated class
                        handles.

    """

    def decorate(cls):
        """
        Register the handler cls.

        :param cls:     Class to register.
        :return:        Unmodified class.

        """
        for state_type in args:
            if state_type in _STATE_HANDLERS:
                raise Exception(f'{state_type} is already registered')
            _STATE_HANDLERS[state_type] = cls
        return cls

    return decorate


# ------------------------------------------------------------------------------
class LavaStateItem:
    """
    Base class for different state item types.

    Use the factory methods `new()`/ `get()` rather than the constructor.

    :param state_id:        State ID.
    :param realm:           Lava realm.
    :param value:           State value.
    :param state_type:      State storage type (e.g. `json`, `raw`, `secure`).
    :param publisher:       An arbitrary label for the identity of the state
                            item creator. Lava itself doesn't use this.
    :param ttl:             Time to live for the state item. Can be a value
                            in seconds or a duration (e.g. `2h`). If greater
                            than the maximum specified for the realm, it will
                            be silently reduced to that value.
    :param aws_session:     A boto3 session. One is created if not specified.
    :param kwargs:          Vestigial. This is not the parameter you're looking for.
    """

    # --------------------------------------------------------------------------
    def __init__(
        self,
        state_id: str,
        realm: str,
        value: Any,
        state_type: str = None,
        publisher: str = None,
        ttl: str | int | float = None,
        aws_session: boto3.Session = None,
        **kwargs,
    ):
        """Use the factory methods `new()`/ `get()` rather than the constructor."""

        self.aws_session = aws_session or boto3.Session()

        # We need some config variables from the realms table. Normally the lava
        # worker loads all this but if we are using this as a standalone module
        # we need to make sure the realms table has been read.
        config_load(realm, aws_session=self.aws_session)

        self.ttl = min(
            duration_to_seconds(ttl or config('STATE_TTL')),
            config('STATE_MAX_TTL', duration_to_seconds),
        )
        self.state_id = state_id
        self.value = value
        self.state_type = state_type or STATE_DEFAULT_TYPE
        self.realm = realm
        self.publisher = publisher
        self.timestamp = None  # Set when a put() is done
        self._state_table = None

    # --------------------------------------------------------------------------
    @classmethod
    def new(cls, state_type=None, *args, **kwargs) -> LavaStateItemType:
        """
        Create a new state item.

        :param state_type:      The state type.
        :param args:            Passed to the constructor.
        :param kwargs:          Passed to the constructor.
        :return:                A state handler for the specified state type.
        """

        try:
            handler = _STATE_HANDLERS[state_type or STATE_DEFAULT_TYPE]
        except KeyError:
            raise LavaError(f'{state_type}: No such state type')

        return handler(*args, state_type=state_type, **kwargs)

    # --------------------------------------------------------------------------
    @classmethod
    def get(cls, state_id: str, realm: str, aws_session: boto3.Session = None) -> LavaStateItemType:
        """
        Retrieve an existing state item from DynamoDB.

        :param state_id:        State ID.
        :param realm:           Lava realm.
        :param aws_session:     A boto3 session. One is created if not specified.

        :return:                A state handler for the specified state type
                                with the value loaded.

        :raise KeyError:        If the state item doesn't exist.
        :raise LavaError:   For other errors.
        """

        if not aws_session:
            aws_session = boto3.Session()
        state_table = aws_session.resource('dynamodb').Table(f'lava.{realm}.state')

        # ----------------------------------------
        # Get the entry from DynamoDB, validate it and get a handler.

        # OK to throw a KeyError here.
        state_entry = state_table.get_item(Key={'state_id': state_id}, ConsistentRead=True)['Item']

        try:
            dict_check(state_entry, required=STATE_REQUIRED_FIELDS, optional=STATE_OPTIONAL_FIELDS)
        except ValueError as e:
            raise LavaError(f'Bad state item: {e}')

        try:
            handler = _STATE_HANDLERS[state_entry['type']]
        except KeyError:
            raise LavaError(f'Unknown state type: {state_entry["type"]}')

        LOG.debug('Got state item for state_id %s', state_id)

        # ----------------------------------------
        # Decode the value using the handler and instantiate it.

        # noinspection PyProtectedMember
        item = handler(
            state_id=state_id,
            value=None,
            state_type=state_entry['type'],
            realm=realm,
            publisher=state_entry.get('publisher'),
            aws_session=aws_session,
        )  # type: LavaStateItem
        item.value = item._decode(state_entry['value'])  # noqa: SLF001
        if 'timestamp' in state_entry:
            item.timestamp = parse(state_entry['timestamp'])
        item._state_table = state_table  # noqa: SLF001

        LOG.debug('Retrieved state item: %s', item)
        return item

    # --------------------------------------------------------------------------
    def __str__(self):
        """Rough and ready str version."""
        return (
            f"{self.__class__.__name__}"
            f"(state_id='{self.state_id}', "
            f"value={self.value},"
            f"publisher='{self.publisher}', "
            f"timestamp={self.timestamp})"
        )

    # --------------------------------------------------------------------------
    def put(self):
        """Encode the value and put it in DynamoDB."""

        if not self._state_table:
            self._state_table = self.aws_session.resource('dynamodb').Table(
                f'lava.{self.realm}.state'
            )

        self.timestamp = now_tz()
        item = {
            'state_id': self.state_id,
            'type': self.state_type,
            'value': self._encode(self.value),
            'timestamp': self.timestamp.isoformat(),
            'ttl': int(datetime.now().timestamp() + self.ttl),
        }
        if self.publisher:
            item['publisher'] = self.publisher
        try:
            self._state_table.put_item(Item=item, ReturnValues='NONE')
        except Exception as e:
            raise LavaError(f'Cannot put state item: {e}')

        LOG.debug('Put state item for state_id %s', self.state_id)

    # --------------------------------------------------------------------------
    def _encode(self, raw: Any) -> Any:
        """Transform an object into a type that can be stored in DynamoDB."""

        raise NotImplementedError('_encode')

    # --------------------------------------------------------------------------
    def _decode(self, cooked: Any) -> Any:
        """Transform a value from DynamoDB into an object."""

        raise NotImplementedError('_decode')


# ------------------------------------------------------------------------------
@state('raw')
class LavaStateRaw(LavaStateItem):
    """State entry with no transformation (don't use for sensitive data)."""

    # --------------------------------------------------------------------------
    def _encode(self, raw: Any) -> Any:
        """For raw state items this is a pass through."""

        return raw

    # --------------------------------------------------------------------------
    def _decode(self, cooked: Any) -> Any:
        """For raw state items this is a pass through."""

        return cooked


# ------------------------------------------------------------------------------
@state('json')
class LavaStateJson(LavaStateItem):
    """State entry with body as JSON encoded string (don't use for sensitive data)."""

    # --------------------------------------------------------------------------
    def _encode(self, raw: Any) -> Any:
        """JSON encode."""

        return json.dumps(raw, default=json_default)

    # --------------------------------------------------------------------------
    def _decode(self, cooked: Any) -> Any:
        """JSON decode."""

        return json.loads(cooked)


# ------------------------------------------------------------------------------
@state('secure')
class LavaStateSecure(LavaStateItem):
    """
    State entry with body as encrypted JSON encoded string.

    Parameter are as for the superclass with the addition of kms_key

    :param kms_key:     ARN or alias (as `alias/...`) of KMS key to encrypt the
                        value. Defaults to the realm system key.
    """

    # --------------------------------------------------------------------------
    def __init__(self, *args, kms_key: str = None, **kwargs):
        """As for super but with kms_key."""

        super().__init__(*args, **kwargs)
        self.kms_key = kms_key or f'alias/lava-{self.realm}-sys'
        self._kms = self.aws_session.client('kms')

    # --------------------------------------------------------------------------
    def _encode(self, raw: Any) -> Any:
        """JSON encode and encrypt."""

        plaintext = json.dumps(raw, default=json_default).encode('utf-8')

        return Binary(self._kms.encrypt(KeyId=self.kms_key, Plaintext=plaintext)['CiphertextBlob'])

    # --------------------------------------------------------------------------
    def _decode(self, cooked: Any) -> Any:
        """JSON decode."""

        if not isinstance(cooked, Binary):
            raise ValueError(
                f'Expected DynamoDB Binary type for secure state item value - got {type(cooked)}'
            )

        return json.loads(self._kms.decrypt(CiphertextBlob=cooked.value)['Plaintext'])
