"""Handlers for loop value generators for the foreach job type."""

from __future__ import annotations

import json
from abc import ABC, abstractmethod
from collections.abc import Callable, Iterable, Iterator
from csv import DictReader
from fnmatch import fnmatchcase
from typing import Any

import boto3
import jinja2
from smart_open import open  # noqa A004

from lava.connection import get_pysql_connection
from lava.connection.core import make_application_name
from lava.lib.misc import dict_check
from .config import LOG
from .lavacore import LavaError


# ------------------------------------------------------------------------------
class Foreach(ABC):
    """
    Abstract base clase for a foreach generator.

    This is also a context manager.

    :param foreach_spec:    A dictionary of control info for the loop generator.
                            Must include a "type" field.
    :param job_id:          Job ID.
    :param realm:           Lava realm.
    :param aws_session:     A boto3 Session(). If not specified a default will
                            be created if required. Default None.
    """

    _FOREACH_HANDLERS = {}
    REQUIRED_FIELDS = ('type',)  # Generally must override in subclass.
    OPTIONAL_FIELDS = ()
    RENDERED_FIELDS = ()  # Override in subclass if we want to render any string fields

    # --------------------------------------------------------------------------
    @classmethod
    def register(cls, *args: str) -> Callable:
        """
        Register foreach handler classes.

        Usage:

        ```python
        @Foreach.register(foreach_type1, ...)
        a_class(...)
        ```

        :param args:        A list of foreach loop types that the decorated class
                            handles.
        :type args:         str
        """

        def decorate(handler_cls: type) -> type:
            """
            Register the handler cls.

            :param handler_cls: Class to register.
            :return:            Unmodified class.

            """
            for foreach_type in args:
                if foreach_type in cls._FOREACH_HANDLERS:
                    raise LavaError(f'{foreach_type} is already registered')
                cls._FOREACH_HANDLERS[foreach_type] = handler_cls
            return handler_cls

        return decorate

    # --------------------------------------------------------------------------
    @classmethod
    def handler(cls, foreach_spec: dict[str, Any], *args, **kwargs) -> Foreach:
        """
        Create a handler instance for the specified foreach loop type.

        The appropriate handler is selected by looking at the `type` in the
        foreach spec.

        :param foreach_spec:   Lava connection spec. The handler required is
                            determined from the type field.

        :param args:        Passed to the handler init.
        :param kwargs:      Passed to the handler init.
        """

        try:
            return cls._FOREACH_HANDLERS[foreach_spec['type']](foreach_spec, *args, **kwargs)
        except KeyError:
            raise LavaError(f'No foreach handler for type {foreach_spec["type"]}')

    # --------------------------------------------------------------------------
    def __init__(
        self,
        foreach_spec: dict[str, Any],
        job_id: str,
        realm: str,
        render_vars: dict[str, Any] = None,
        aws_session: boto3.Session = None,
    ):
        """Create a foreach loop generator instance."""

        dict_check(foreach_spec, required=self.REQUIRED_FIELDS, optional=self.OPTIONAL_FIELDS)
        self.foreach_spec = foreach_spec
        self.render_vars = render_vars
        self.job_id = job_id
        self.realm = realm
        self.aws_session = aws_session or boto3.Session()
        self._render()

    # --------------------------------------------------------------------------
    def _render(self) -> None:
        """Jinja render selected fields in the foreach spec."""

        if not self.render_vars:
            return

        for k in self.RENDERED_FIELDS:
            if isinstance(val := self.foreach_spec.get(k), str):
                self.foreach_spec[k] = jinja2.Template(val).render(**self.render_vars)

    # --------------------------------------------------------------------------
    def __enter__(self) -> Foreach:
        """Context manager open."""

        LOG.debug('Entering context for Foreach: %s', self.foreach_spec['type'])
        return self

    # --------------------------------------------------------------------------
    def __exit__(self, *args, **kwargs):
        """Context manager exit."""

        LOG.debug('Exiting context for Foreach: %s', self.foreach_spec['type'])
        self.close()

    # --------------------------------------------------------------------------
    # noinspection PyMethodMayBeStatic
    def close(self) -> None:  # noqa B027
        """Close the foreach looper."""

        pass

    # --------------------------------------------------------------------------
    @abstractmethod
    def __iter__(self) -> Iterator[dict[str, Any]]:
        """Construct the iterable."""

        raise NotImplementedError('__next__')


# ------------------------------------------------------------------------------
@Foreach.register('range')
class _ForeachRange(Foreach):
    """
    A simple numerically controlled loop with semantics like a Python range().

    The foreach spec has the following elements.

    -   type:   Loop type. Required.
    -   stop:   As for a Python rnage. Required.
    -   start:  As for a Python range.
    -   step:   As for a Python rnage.
    -   name:   The name of global variable to which the counter value is assigned.
                If not specified, the counter value is not returned but the loop
                still executes.
    """

    REQUIRED_FIELDS = ('type', 'stop')
    OPTIONAL_FIELDS = ('start', 'step', 'name')

    # --------------------------------------------------------------------------
    def __iter__(self) -> Iterator[dict[str, Any]]:
        """Construct the iterable."""

        name: str = self.foreach_spec.get('name')
        if name and name.lower().startswith('lava'):
            raise LavaError('foreach field names may not start with "lava"')

        for n in range(
            int(self.foreach_spec.get('start', 0)),
            int(self.foreach_spec['stop']),
            int(self.foreach_spec.get('step', 1)),
        ):
            yield {name: n} if name else {}


# ------------------------------------------------------------------------------
@Foreach.register('inline')
class _ForeachInline(Foreach):
    """
    A foreach controller with Loop values embedded in the foreach_spec.

    There is no requirement for each dict in the sequence of values to have the
    same keys but it would be a pretty odd lava job that tried to use that.

    The foreach spec has the following elements.

    -   type:   Loop type. Required.
    -   values: An iterable of dictionaries. Required.

    """

    REQUIRED_FIELDS = ('type', 'values')

    # --------------------------------------------------------------------------
    def __init__(self, foreach_spec: dict[str, Any], *args, **kwargs):
        """Init."""

        super().__init__(foreach_spec, *args, **kwargs)
        if not isinstance(foreach_spec['values'], Iterable):
            raise LavaError('values must be a sequence of objects')

    # --------------------------------------------------------------------------
    def __iter__(self) -> Iterator[dict[str, Any]]:
        """Construct the iterable."""

        for d in self.foreach_spec['values']:
            if any(k.lower().startswith('lava') for k in d):
                raise LavaError('foreach field names may not start with "lava"')
            yield d


# ------------------------------------------------------------------------------
@Foreach.register('jsonl')
class _ForeachJsonl(Foreach):
    """
    A foreach controller that reads JSON objects from a file, one per line.

    There is no requirement for each JSON object in the file to have the
    same keys but it would be a pretty odd lava job that tried to use that.

    The foreach spec has the following elements.

    -   type:     Loop type. Required.
    -   filename: File contain one-line JSON objects. Can be local or S3. Required.

    """

    REQUIRED_FIELDS = ('type', 'filename')
    RENDERED_FIELDS = ('filename',)

    # --------------------------------------------------------------------------
    def __init__(self, foreach_spec: dict[str, Any], *args, **kwargs):
        """Init."""

        super().__init__(foreach_spec, *args, **kwargs)
        self.fp = None

    # --------------------------------------------------------------------------
    def __enter__(self) -> Foreach:
        """Context manager open."""

        LOG.debug('Entering context for Foreach: %s', self.foreach_spec['type'])

        self.fp = open(
            self.foreach_spec['filename'],
            transport_params={'client': self.aws_session.client('s3')},
        )
        return self

    # --------------------------------------------------------------------------
    def close(self) -> None:
        """Close the foreach looper."""

        if self.fp:
            self.fp.close()

    # --------------------------------------------------------------------------
    def __iter__(self) -> Iterator[dict[str, Any]]:
        """Construct the iterable."""

        if not self.fp:
            raise LavaError(f'Internal error: {self.__class__.__name__} expected open file')

        for lineno, s in enumerate(self.fp, 1):
            try:
                d = json.loads(s)
            except Exception as e:
                raise LavaError(f'{self.foreach_spec["filename"]}: line {lineno}: {e}')

            if any(k.lower().startswith('lava') for k in d):
                raise LavaError('foreach field names may not start with "lava"')

            yield d


# ------------------------------------------------------------------------------
@Foreach.register('csv')
class _ForeachCsv(Foreach):
    """
    A foreach controller that reads iteration values from a CSV file.

    The foreach spec has the following elements.

    -   type:     Loop type. Required.
    -   filename: CSV file. Can be local or S3. Required.

    """

    REQUIRED_FIELDS = ('type', 'filename')
    RENDERED_FIELDS = ('filename',)

    # --------------------------------------------------------------------------
    def __init__(self, foreach_spec: dict[str, Any], *args, **kwargs):
        """Init."""

        super().__init__(foreach_spec, *args, **kwargs)
        self.fp = None

    # --------------------------------------------------------------------------
    def __enter__(self) -> Foreach:
        """Context manager open."""

        LOG.debug('Entering context for Foreach: %s', self.foreach_spec['type'])

        self.fp = open(
            self.foreach_spec['filename'],
            'rt',
            transport_params={'client': self.aws_session.client('s3')},
        )
        return self

    # --------------------------------------------------------------------------
    def close(self) -> None:
        """Close the foreach looper."""

        if self.fp:
            self.fp.close()

    # --------------------------------------------------------------------------
    def __iter__(self) -> Iterator[dict[str, Any]]:
        """Construct the iterable."""

        if not self.fp:
            raise LavaError(f'Internal error: {self.__class__.__name__} expected open file')

        reader = DictReader(self.fp)
        if any(k.lower().startswith('lava') for k in reader.fieldnames):
            raise LavaError('foreach field names may not start with "lava"')
        return reader


# ------------------------------------------------------------------------------
@Foreach.register('query')
class _ForeachQuery(Foreach):
    """
    A foreach controller that reads iteration values from a database query.

    We do not permit rendering of the SQL query to avoid SQL injection.

    The foreach spec has the following elements.

    -   type:    Loop type. Required.
    -   conn_id: A database connection ID. Required.
    -   query:   An SQL query. This is used as is. Nothing fancy. No rendering.
                 Required.

    """

    REQUIRED_FIELDS = ('type', 'conn_id', 'query')

    # --------------------------------------------------------------------------
    def __init__(self, foreach_spec: dict[str, Any], *args, **kwargs):
        """Init."""

        super().__init__(foreach_spec, *args, **kwargs)
        self.conn = None

    # --------------------------------------------------------------------------
    def __enter__(self) -> Foreach:
        """Context manager open."""

        LOG.debug('Entering context for Foreach: %s', self.foreach_spec['type'])

        self.conn = get_pysql_connection(
            self.foreach_spec['conn_id'],
            self.realm,
            aws_session=self.aws_session,
            application_name=make_application_name(
                conn_id=self.foreach_spec['conn_id'],
                realm=self.realm,
                job_id=self.job_id,
            ),
        )
        return self

    # --------------------------------------------------------------------------
    def close(self) -> None:
        """Close the foreach looper."""

        if self.conn:
            self.conn.close()

    # --------------------------------------------------------------------------
    def __iter__(self) -> Iterator[dict[str, Any]]:
        """Construct the iterable."""

        if not self.conn:
            raise LavaError(f'Internal error: {self.__class__.__name__} expected open connection')

        cursor = self.conn.cursor()
        cursor.execute(self.foreach_spec['query'])
        column_names = tuple(c[0] for c in cursor.description)
        if any(c.lower().startswith('lava') for c in column_names):
            raise LavaError('foreach field names may not start with "lava"')

        while True:
            if not (row := cursor.fetchone()):
                break
            yield dict(zip(column_names, row))


# ------------------------------------------------------------------------------
@Foreach.register('s3list')
class _ForeachS3list(Foreach):
    """A foreach controller that lists objects in an S3 prefix."""

    REQUIRED_FIELDS = ('type', 'bucket')
    OPTIONAL_FIELDS = ('glob', 'prefix')
    RENDERED_FIELDS = ('bucket', 'prefix')

    # --------------------------------------------------------------------------
    def __init__(self, foreach_spec: dict[str, Any], *args, **kwargs):
        """Init."""

        super().__init__(foreach_spec, *args, **kwargs)
        self.s3 = self.aws_session.client('s3')
        if isinstance(foreach_spec.get('glob'), str):
            self.foreach_spec['glob'] = [self.foreach_spec['glob']]

    # --------------------------------------------------------------------------
    def __iter__(self) -> Iterator[dict[str, Any]]:
        """
        Construct the iterable.

        Each element is a dictionary like this, as per what is returned by boto3
        S3 client `list_objects_v2()` but with `Bucket` added.

        ```python
        {
            's3obj': {
                'Bucket': 'my-bucket',
                'Key': 'a/filename/in/s3',
                'LastModified': datetime.datetime(2024, 1, 1, 6, 2, 59, tzinfo=tzutc()),
                'ETag': '"be0c0123456789abcd0123456678916a"',
                'Size': 197,
                'StorageClass': 'STANDARD'
            }
        }
        ```

        """

        globs = self.foreach_spec.get('glob')
        paginator = self.s3.get_paginator('list_objects_v2')
        bucket = self.foreach_spec['bucket']
        for response in paginator.paginate(
            Bucket=bucket, Prefix=self.foreach_spec.get('prefix', '')
        ):
            for s3obj in response.get('Contents', []):
                key = s3obj['Key']
                if not globs or any(fnmatchcase(key, g) for g in globs):
                    s3obj['Bucket'] = bucket
                    yield {'s3obj': s3obj}
