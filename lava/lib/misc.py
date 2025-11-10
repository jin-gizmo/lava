"""Miscellaneous utilities."""

from __future__ import annotations

import hashlib
import importlib
import json
import os
import re
import unicodedata
from collections.abc import Callable, Hashable, Iterable, Iterator, MutableMapping
from contextlib import contextmanager, suppress
from copy import deepcopy
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from decimal import Decimal
from fnmatch import fnmatchcase
from logging import Logger
from pathlib import Path
from threading import Lock
from types import ModuleType
from typing import Any

from .datetime import timedelta_to_str

__author__ = 'Murray Andrews'

# Default hashing algorithm
HASH_ALGORITHM = 'sha256'


# ------------------------------------------------------------------------------
SIZE_UNITS = {
    'B': 1,
    'K': 1000,
    'KB': 1000,
    'M': 1000**2,
    'MB': 1000**2,
    'G': 1000**3,
    'GB': 1000**3,
    'T': 1000**4,
    'TB': 1000**4,
    'P': 1000**5,
    'PB': 1000**5,
    'KiB': 1024,
    'MiB': 1024**2,
    'GiB': 1024**3,
    'TiB': 1024**4,
    'PiB': 1024**5,
}
SIZE_REGEX = (
    r'\s*((?P<value>[+-]?(\d+(\.\d*)?|\.\d+)([eE][+-]?\d+)?)\s*'
    r'(?P<units>{units}))\s*$'.format(units='|'.join(SIZE_UNITS.keys()))
)


def size_to_bytes(size: str | int) -> int:
    """
    Convert a string specifying a data size to a number of bytes.

    :param size:        String in the form nnnX where nnn is an integer or float
                        and X is one of (case sensitive):
                        'B'         Bytes
                        'K', 'KB':  Kilobytes (1000)
                        'M', 'MB':  Megabytes
                        'G', 'GB':  Gigabytes
                        'T', 'TB':  Terabytes
                        'P', 'PB':  Petabytes.
                        'KiB':      Kibibytes (1024)
                        'MiB':      Mebibytes
                        'GiB':      Gibibytes
                        'TiB':      Tebibytes
                        'PiB':      Pebibytes

                        Whitespace is ignored.  Note a leading + or - will be
                        handled correctly as will exponentials. If no multiplier
                        suffix is provided, bytes are assumed.

    :return:            The size in bytes.

    :raise ValueError:  If the input is malformed.

    """

    try:
        return int(size)
    except ValueError:
        pass

    if not isinstance(size, str):
        raise ValueError(f'Invalid size type: {type(size)}')

    m = re.match(SIZE_REGEX, size)

    if not m:
        raise ValueError('Invalid size: ' + size)

    return int(round(float(m.group('value')) * SIZE_UNITS[m.group('units')], 0))


# ------------------------------------------------------------------------------
def glob_strip(names: Iterable[str], patterns: str | Iterable[str]) -> set[str]:
    """
    Remove from an iterable of strings any that match any of the given patterns.

    Patterns are glob style. Case is significant.

    The result is returned as a set so any ordering is lost.

    :param names:       An iterable of strings to match.
    :param patterns:    A glob pattern or iterable of glob patterns.

    :return:            A set containing all input strings that don't match any
                        of the glob patterns.
    """

    names = set(names)
    if isinstance(patterns, str):
        patterns = [patterns]

    for p in patterns:
        names -= {n for n in names if fnmatchcase(n, p)}

    return names


# ------------------------------------------------------------------------------
def dict_check(
    d: dict[str, Any],
    required: Iterable[str] = None,
    optional: Iterable[str] = None,
    ignore: str | Iterable[str] = None,
) -> None:
    """
    Check that the given dictionary has the required keys.

    !!! note "Patheric attempt at exculpation ..."
        This is a horrible implementation of good intentions dating from the year
        dot. Sorry. If we were doing it all again, we'd use a proper object model
        with Pydantic, or something like that.

    :param d:           The dict to check.
    :param required:    An iterable of mandatory keys. Can be None indicating
                        required keys should not be checked.
    :param optional:    An iterable of optional keys. Can be None indicating
                        optional keys should not be checked.
    :param ignore:      Ignore any keys that match the specified glob pattern
                        or list of patterns.

    :raise ValueError:  If the dict doesn't contain all required keys or does
                        contain disallowed keys.
    """

    if required is not None and not isinstance(required, set):
        # noinspection PyTypeChecker
        required = set(required)
    if optional is not None and not isinstance(optional, set):
        optional = set(optional)

    actual_keys = set(d)

    # Remove the ignore keys from everything required and actual keys.
    # No need to remove from optionals.
    if ignore:
        if isinstance(ignore, str):
            ignore = [ignore]
        if required:
            required = glob_strip(required, ignore)
        actual_keys = glob_strip(actual_keys, ignore)

    if required is not None and not required <= actual_keys:
        raise ValueError('Missing keys: {}'.format(', '.join(sorted(required - actual_keys))))

    if optional is not None:
        bad_keys = actual_keys - (required if required is not None else set()) - optional
        if bad_keys:
            raise ValueError('Unexpected keys: {}'.format(', '.join(sorted(bad_keys))))


# -------------------------------------------------------------------------------
def import_by_name(name: str, parent: str = None) -> ModuleType:
    """
    Import a named module from within the named parent.

    :param name:            The name of the required module.
    :param parent:          Name of parent module. Default None.

    :return:                The sender module.

    :raise ImportError:     If the import fails.

    """

    if parent:
        name = parent + '.' + name

    return importlib.import_module(name)


# ------------------------------------------------------------------------------
def json_default(obj: Any) -> Any:
    """
    Serialise non-standard objects for json.dumps().

    This is a helper function for JSON serialisation with json.dumps() to allow
    (UTC) datetime and time objects to be serialised. It should be used thus:

    ```python
    json_string = json.dumps(object_of_some_kind, default=json_default)
    ```

    It is primarily used in API responses.

    :param obj:             An object.
    :return:                A serialisable version. For datetime objects we just
                            convert them to a string that strptime() could handle.

    :raise TypeError:       If obj cannot be serialised.
    """

    if isinstance(obj, datetime):
        return obj.isoformat()

    if isinstance(obj, timedelta):
        return timedelta_to_str(obj)

    if isinstance(obj, Decimal):
        return float(obj) if '.' in str(obj) else int(obj)

    try:
        return str(obj)
    except Exception:
        raise TypeError(f'Cannot serialize {type(obj)}')


# ------------------------------------------------------------------------------
def sepjoin(sep: str, *args: str | list[str]) -> str:
    """
    Join all the non-empty args with the specified separator.

    Any list args are expanded.

    ie. if sep is ``/`` and with args of: ``'a', [], ['b', 'c']'``
    will return ``a/b/c``.

    :param sep:         A separator string used as a joiner.
    :param args:        A string or list of strings.

    :return:            Joined up args separated by /

    """

    result = []
    for s in filter(None, args):
        result.extend(s if isinstance(s, list) else [s])

    return sep.join(result)


# ------------------------------------------------------------------------------
def splitext2(path: str, pathsep: str = os.sep, extsep: str = os.extsep) -> tuple[str, str]:
    """
    Split a string into root + extension.

    This is a variation on os.path.splitext() except that a suffix is defined as
    everything from the first dot in the basename onwards, unlike splitext()
    which uses the last dot in the basename..

    Also splitext() always uses os.sep and os.extsep whereas splitext2 allows
    these to be overridden.

    :param path:        The path.
    :param pathsep:     Path separator. Defaults to os.sep.
    :param extsep:      Suffix separator. Defaults to os.extsep.

    :return:            A tuple (root, ext) such that root + ext == path

    """

    try:
        dirpart, basepart = path.rsplit(pathsep, 1)
    except ValueError:
        dirpart, basepart = '', path

    preprefix = ''
    while basepart.startswith(extsep):
        preprefix += extsep
        basepart = basepart[1:]

    try:
        prefix, suffix = basepart.split(extsep, 1)
        suffix = '.' + suffix

    except ValueError:
        prefix, suffix = basepart, ''

    return sepjoin(pathsep, dirpart, preprefix + prefix), suffix


# ------------------------------------------------------------------------------
def dict_expand_keys(d: dict[str, Any], sep_pat: str = r'\.') -> dict[str, Any]:
    """
    Expand a dictionary whose keys contain a hierarchy separator pattern.

    A new hierarchical dictionary is created and the original dictionary is
    unchanged.

    For example, a dictionary containing { 'a.b': 10 } would be expanded to
    {'a': {'b' : 10}}.


    :param d:           A dictionary with string keys.
    :param sep_pat:     A regular expression used to split dictionary keys into
                        hierarchies. Default is a dot. Be very careful with
                        capture groups. It will almost certainly not do what
                        you expect. If you must use groups, then try using the
                        non-capturing style (?:...).

    :return:            The expanded dictionary.

    :raise ValueError:  If any keys are not strings or paths conflict
    """

    new_d = {}

    for k, v in d.items():
        if not isinstance(k, str):
            raise ValueError(f'Non string key: {k}')

        klist = re.split(sep_pat, k)
        try:
            dict_set_deep(new_d, klist, v)
        except ValueError:
            raise ValueError(f'Path conflict: {k}')

    return new_d


# ------------------------------------------------------------------------------
def dict_strip(d: dict) -> dict:
    """
    Return a new dictionary with all None value elements removed.

    :param d:       Input dictionary.
    :return:        New dict with None value keys removed.

    """

    return {k: v for k, v in d.items() if v is not None}


# ------------------------------------------------------------------------------
def dict_set_deep(d: dict, keys: list[str] | tuple[str], v: Any) -> None:
    """
    Set a value in a dict based on a sequence of keys.

    Subdicts are created on the way as required.

    :param d:           The dictionary.
    :param keys:        A list or tuple of strings.
    :param v:           The value to set.

    :raise ValueError:  If one of the elements along the path is not a dict.

    """

    for k in keys[:-1]:
        # noinspection PyUnresolvedReferences
        d = d.setdefault(k, {})
        if not isinstance(d, dict):
            raise ValueError('Key sequence does not lead to a dict')

    if not isinstance(d, dict):
        raise ValueError('Key sequence does not lead to a dict')

    d[keys[-1]] = v


# ------------------------------------------------------------------------------
def dict_select(d: dict, *keys: Hashable) -> dict:
    """
    Filter a dictionary to create a new dictionary containing only the specified keys.

    :param d:           A dictionary.
    :param keys:        One or more keys.

    :return:            A new dictionary containing only subset of dict wih
                        keys in the given list.

    """

    return {k: v for k, v in d.items() if k in set(keys)}


# ------------------------------------------------------------------------------
def dict_hash(d: dict, ignore: str | Iterable[str] = None, algorithm: str = HASH_ALGORITHM) -> str:
    """
    Calculate an ASCII safe hash on a dictionary.

    !!! warning
        This is not cryptographically secure and should not be used for any
        security related purpose. It's only for change detection without additional
        cryptographic protection.

    :param d:       The dictionary. It must be JSON serialisable.
    :param ignore:  Ignore any keys that match the specified glob pattern
                    or list of patterns.
    :param algorithm: Hashing algorithm. Must be one of the values supported
                    by `hashlib.new()`.
    :return:        An ASCII safe hash.
    """

    if ignore:
        if isinstance(ignore, str):
            ignore = [ignore]
    else:
        ignore = set()

    keys_to_hash = glob_strip(d, ignore)
    dict_to_hash = {k: d[k] for k in keys_to_hash}
    data = json.dumps(dict_to_hash, sort_keys=True, default=json_default).encode('utf-8')
    return hashlib.new(algorithm, data).hexdigest()


# ------------------------------------------------------------------------------
CHECKSUM_DEFAULT_VERSION = 1
CHECKSUM_DEFAULT_TAG = 'LC'


@dataclass
class DictChecksum:
    """Simple representation of a lava style checksum on a dict."""

    hashval: str
    algorithm: str = 'sha256'
    version: int = CHECKSUM_DEFAULT_VERSION
    tag: str = field(default=CHECKSUM_DEFAULT_TAG, compare=False)

    def __post_init__(self):
        """Validate algorithm."""
        if self.algorithm not in hashlib.algorithms_available:
            raise ValueError(
                f'Algorithm must be one of {", ".join(sorted(hashlib.algorithms_guaranteed))}'
            )

    # --------------------------------------------------------------------------
    @classmethod
    def for_dict(
        cls,
        d: dict[str, Any],
        ignore: str | Iterable[str] = None,
        algorithm: str = HASH_ALGORITHM,
        version=CHECKSUM_DEFAULT_VERSION,
        tag: str = CHECKSUM_DEFAULT_TAG,
    ) -> DictChecksum:
        """
        Create a checksum from a dict.

        :param d:       The dictionary. It must be JSON serialisable.
        :param ignore:  Ignore any keys that match the specified glob pattern
                        or list of patterns.
        :param algorithm: Hashing algorithm. Must be one of the values supported
                        by `hashlib.algorithms_guaranteed`.
        :param version: Checksum format version. This version stuff is really
                        just a placeholder in case we change formats in future.
                        Nothing much is done with it at the moment.
        :param tag:     The checksum tag. This is helpful to identify the source
                        of the checksum
        """

        if not isinstance(d, dict):
            raise TypeError(f'{cls.__name__}.from_dict() requires dict not {type(d)}')
        if version != 1:
            raise ValueError('Only checksum format version 1 is currently supported')
        return cls(
            dict_hash(d, ignore=ignore, algorithm=algorithm), algorithm, version=version, tag=tag
        )

    # ------------------------------------------------------------------------------
    @classmethod
    def from_str(cls, s: str) -> DictChecksum:
        """Connvert from representational format."""

        try:
            version, tag, algorithm, hashval = s.split(';')
        except ValueError:
            raise ValueError('Malformed checksum')
        return cls(hashval, algorithm, int(version), tag)

    # ------------------------------------------------------------------------------
    def is_valid_for(self, d: dict, ignore: str | Iterable[str] = None) -> bool:
        """
        Check that this checksum is valid for the given dict.

        :param d:       The dictionary. It must be JSON serialisable.
        :param ignore:  Ignore any keys that match the specified glob pattern
                        or list of patterns.
        """

        return self == self.__class__.for_dict(
            d, ignore=ignore, algorithm=self.algorithm, version=self.version
        )

    # --------------------------------------------------------------------------
    def __str__(self):
        """Construct the representational format."""

        return ';'.join(
            (
                str(self.version),
                self.tag,
                self.algorithm,
                self.hashval,
            )
        )


# ------------------------------------------------------------------------------
def str2bool(s: str | bool) -> bool:
    """
    Convert a string to a boolean.

    This is a (case insensitive) semantic conversion.

        'true', 't', 'yes', 'y', non-zero int as str --> True
        'false', 'f', 'no', 'n', zero as str --> False

    :param s:       A boolean or a string representing a boolean. Whitespace is
                    stripped. Boolean values are passed back unchanged.

    :return:        A boolean derived from the input value.

    :raise ValueError:  If the value cannot be converted.

    """

    if isinstance(s, bool):
        return s

    if not isinstance(s, str):
        raise TypeError(f'Expected str, got {type(s)}')

    t = s.lower().strip()

    if t in ('true', 't', 'yes', 'y'):
        return True

    if t in ('false', 'f', 'no', 'n'):
        return False

    try:
        t = int(t)
    except ValueError:
        pass
    else:
        return bool(t)

    raise ValueError(f'Cannot convert string to bool: {s}')


# ------------------------------------------------------------------------------
def is_quoted(s: str, quote: str = "'") -> bool:
    """
    Return true if the given string is surrounded by the given quote string.

    :param s:           The string to check.
    :param quote:       The quote string. Default is single quote.

    :return:            True if quoted, False otherwise.
    """

    return s.startswith(quote) and s.endswith(quote)


# ------------------------------------------------------------------------------
def listify(v: Any) -> list:
    """
    Convert the argument to a list.

    If it's a string, then it becomes a list of one element (the source string).
    If it's a list, it's returned unchanged. If it is some other kind of iterable,
    it's converted to a list.

    !!! warning
        Be careful when passing a dict as an argument. It will return the keys
        in a list, not a list containing the dict as its only element.

    :param v:           The source var.

    :raise TypeError:   If not iterable.

    """

    if isinstance(v, list):
        return v

    if isinstance(v, str):
        return [v]

    return list(v)


# ------------------------------------------------------------------------------
def clean_str(s: str, safe_chars=None, alternative=None) -> str:
    """
    Clean a string by removing or replacing anything except word chars and safe chars.

    The result will only contain word chars (alphanum + underscore) and the
    specified safe_chars.

    :param s:           The string to clean.
    :param safe_chars:  Safe chars that can remain but not at the beginning or
                        end of the string.
    :param alternative: Replace unsafe chars with the specified alternative.
                        Must be a single character string. If not specified,
                        unsafe chars are removed.
    :return:            The cleaned string.

    :raise ValueError:  If the string cannot be cleansed or the result is empty.
    """

    if not s:
        raise ValueError('clean_str: Empty string')
    if alternative and len(alternative) != 1:
        raise ValueError('clean_str: Alternative must be a single character string')

    s = str(s)
    s = unicodedata.normalize('NFKD', s).encode('ascii', 'ignore').decode('ascii')

    # Remove (or replace) everything except allowed chars.
    remove_pat = rf'[^\w{safe_chars}]+' if safe_chars else r'[^\w]+'
    s = re.sub(remove_pat, alternative or '', s)
    # Must start and end with a word char
    s = re.sub(r'^\W+', '', s)
    s = re.sub(r'^\W+$', '', s)

    if not s:
        raise ValueError('clean_str: Result is empty')

    return s


# ------------------------------------------------------------------------------
HTML_RE = re.compile(r'\s*(<html|<!DOCTYPE\s+html)', re.IGNORECASE)


def is_html(s: str) -> bool:
    """
    Try to guess if the given string is HTML.

    :param s:       A string.
    :return:        True if string appears to be HTML, False otherwise.

    """

    return HTML_RE.match(s) is not None


# ------------------------------------------------------------------------------
def match_any(s: str, globs: list[str], ignore_case: bool = False) -> bool:
    """
    Check if a string matches any glob pattern in a list of patterns.

    :param s:           The string to match.
    :param globs:       A list of glob style patterns.
    :param ignore_case: If True ignore case.
    :return:            True if the string matches any pattern, False otherwise.
    """

    if ignore_case:
        s = s.lower()
        globs = [g.lower() for g in globs]

    return any(fnmatchcase(s, pattern) for pattern in globs)


# ------------------------------------------------------------------------------
def match_none(s: str, globs: list[str], ignore_case: bool = False) -> bool:
    """
    Check that a string matches none of the glob pattern in a list of patterns.

    :param s:           The string to match.
    :param globs:       A list of glob style patterns.
    :param ignore_case: If True igore case.
    :return:            False if the string matches any pattern, True otherwise.
    """

    return not match_any(s, globs, ignore_case=ignore_case)


# ------------------------------------------------------------------------------
def decimal_to_scalar(d: Decimal) -> int | float:
    """
    Convert a decimal to an int or float, whichever is more appropriate.

    :param d:       A decimal.
    :return:        An equivalent int or float.
    """

    int_d = int(d)
    return int_d if int_d == d else float(d)


# ------------------------------------------------------------------------------
@dataclass
class Task:
    """Basic task model."""

    description: str
    action: Callable
    args: list[Any] | None = None
    kwargs: dict[str, Any] | None = None


@dataclass
class TaskResult:
    """Result of running a task."""

    task: Task
    result: Any
    exception: Exception | None


# ------------------------------------------------------------------------------
class Defer:
    """
    Class to manage deferred tasks.

    There is only one singleton per event type.

    This has some similarities to [atexit](https://docs.python.org/3/library/atexit.html)
    but with a bit more flexibility.

    !!! warning
        Do NOT instantiate this directly. Use Defer.on_event().

    :param event:   A label indicating the event for which the deferred tasks
                    are waiting.

    """

    _event_lock = Lock()

    events = {}

    # --------------------------------------------------------------------------
    @classmethod
    def on_event(cls, event: str) -> Defer:
        """
        Create or retrieve the deferred task handler for the given event.

        This is a factory method to make sure this is a singleton for each event
        type.

        :param event:   A label indicating the event for which the deferred tasks
                        are waiting.
        """

        with cls._event_lock:
            if event not in cls.events:
                cls.events[event] = cls(event)
            return cls.events[event]

    # --------------------------------------------------------------------------
    def __init__(self, event: str):
        """Create a singleton deferral register for a given event type."""

        self.event = event
        self.tasks: dict[int, Task] = {}
        self._task_id = 0
        self._task_lock = Lock()

    # --------------------------------------------------------------------------
    def add(self, task: Task) -> int:
        """
        Add a deferred task.

        :param task:        The task to be added.
        :return:            A unique identifier for the task that can be used to
                            cancel it.
        """

        with self._task_lock:
            self._task_id += 1
            self.tasks[self._task_id] = task
            return self._task_id

    # --------------------------------------------------------------------------
    def cancel(self, task_id: int) -> None:
        """
        Cancel the specified task.

        :param task_id:     The ID of the task when it was created.
        """

        with self._task_lock, suppress(KeyError):
            del self.tasks[task_id]

    # --------------------------------------------------------------------------
    def run(self, logger: Logger = None) -> list[TaskResult]:
        """
        Run all the registered tasks in a last in, first out order.

        :param logger:  If specified, activity will be sent to the logger.
        """

        results = []
        for _, t in sorted(self.tasks.items(), reverse=True):
            try:
                results.append(TaskResult(t, t.action(*(t.args or []), **(t.kwargs or {})), None))
                if logger:
                    logger.info('Deferred[%s]: %s: OK', self.event, t.description)
            except Exception as e:
                results.append(TaskResult(t, None, e))
                if logger:
                    logger.error('Deferred[%s]: %s: %s', self.event, t.description, e)

        return results


# ------------------------------------------------------------------------------
class TrackedMapping(MutableMapping):
    """
    Catch and record references to dictionary items (known and unknown).

    :param data:      The data dictionary being tracked.
    """

    def __init__(self, data: dict[str, Any], default_factory: Callable = None):
        """Catch references to unknown items and attributes and record them."""

        self._data = deepcopy(data)
        self._default_factory = default_factory
        self.unknown_refs = set()
        self.visited_refs = set()

    def __len__(self) -> int:
        """Get length of underlying data."""
        return len(self._data)

    def __getitem__(self, key: str) -> Any:
        """
        Get an element from the data and record missing ones.

        An element that haa to be supplied by the default_factory is still
        considered to have been missing ... and visited.
        """

        if key in self._data:
            self.visited_refs.add(key)
            return self._data[key]

        # If we need to use the factory the item is both unknown and visited!
        self.unknown_refs.add(key)

        if self._default_factory:
            self._data[key] = self._default_factory()
            self.visited_refs.add(key)
            return self._data[key]

        raise KeyError(key)

    def __setitem__(self, key, value, /):
        """Set an element."""

        self._data[key] = value

    def __iter__(self) -> Iterator[Any]:
        """Iterate over the elements."""

        return iter(self._data)

    def __delitem__(self, key):
        """Delete item from underlying data."""

        del self._data[key]

    def __repr__(self):
        """Convert to repr."""
        return f'{self.__class__.__name__}({self._data!r})'

    def __str__(self):
        """Convert to string."""
        return str(self._data)


# ------------------------------------------------------------------------------
def format_dict_unescaped(obj: dict, _depth=0) -> str:
    """
    Create a string representaiton of an object without escaped strings.

    Use case for this is _very_ specialised. Tread carefully.
    """

    if isinstance(obj, dict):
        if not obj:
            return '{}'

        items = []
        prefix = ' ' * _depth * 4
        for key, value in obj.items():
            if isinstance(value, str):
                # Don't quote strings - show them raw
                formatted_value = value
            elif isinstance(value, dict):
                formatted_value = format_dict_unescaped(value, _depth + 1)
            elif isinstance(value, (list, tuple)):
                formatted_value = format_sequence_unescaped(value, _depth + 1)
            else:
                formatted_value = repr(value)

            items.append(f'{prefix}    {key!r}: {formatted_value}')

        return '{\n' + ',\n'.join(items) + f'\n{prefix}}}'

    return repr(obj)


# ------------------------------------------------------------------------------
def format_sequence_unescaped(seq: list | tuple, _depth=0) -> str:
    """Create a string representaiton of a sequence without escaped strings."""

    if not seq:
        return '[]' if isinstance(seq, list) else '()'

    items = []
    prefix = ' ' * _depth * 4
    for item in seq:
        if isinstance(item, str):
            formatted_item = item
        elif isinstance(item, dict):
            formatted_item = format_dict_unescaped(item, _depth + 1)
        else:
            formatted_item = repr(item)
        items.append(f'{prefix}    {formatted_item}')

    brackets = '[]' if isinstance(seq, list) else '()'
    return f'{brackets[0]}\n' + ',\n'.join(items) + f'\n{prefix}{brackets[-1]}'


# ------------------------------------------------------------------------------
@contextmanager
def pythonpath_prepended(path: str | Path):
    """Temporarily prepend a path to PYTHONPATH."""

    if not isinstance(path, str):
        path = str(path)
    path_orig = os.environ.get('PYTHONPATH')
    try:
        os.environ['PYTHONPATH'] = os.pathsep.join([path, path_orig]) if path_orig else path
        yield
    finally:
        if path_orig is None:
            os.environ.pop('PYTHONPATH', None)
        else:
            os.environ['PYTHONPATH'] = path_orig
