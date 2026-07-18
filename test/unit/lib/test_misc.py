"""Test lava misc utils."""

from __future__ import annotations

import logging
from datetime import date, time, timezone

import pytest

from lava.lib.misc import *


# ------------------------------------------------------------------------------
@pytest.mark.parametrize(
    's,expected',
    [
        (30, 30),
        ('30', 30),
        ('30B', 30),
        ('30 B', 30),
        ('30 K', 30 * 1000),
        ('30 KB', 30 * 1000),
        ('30 MB', 30 * 1_000_000),
        ('30 GiB', 30 * 1024**3),
    ],
)
def test_size_to_bytes_ok(s, expected):
    assert size_to_bytes(s) == expected


@pytest.mark.parametrize(
    's',
    [
        [],  # Not numeric or size spec
        b'No-bytes',
        'bad-size',
        '30k',
    ],
)
def test_size_to_bytes_bad(s):
    # noinspection PyTypeChecker
    with pytest.raises((ValueError, TypeError)):
        size_to_bytes(s)


# ------------------------------------------------------------------------------
@pytest.mark.parametrize(
    'names,patterns,expected',
    [
        (['abc', 'def'], '*e*', {'abc'}),
        (('abc', 'def'), ('*e*',), {'abc'}),
        (('abc', 'def'), ('no-found',), {'def', 'abc'}),
    ],
)
def test_glob_strip_ok(names, patterns, expected):
    assert glob_strip(names, patterns) == expected


# ------------------------------------------------------------------------------
@pytest.mark.parametrize(
    'v,expected',
    [
        (datetime(2024, 1, 31, 8, 20, 30), '2024-01-31T08:20:30'),
        (datetime(2024, 1, 31, 8, 20, 30, microsecond=40), '2024-01-31T08:20:30.000040'),
        (datetime(2024, 1, 31, 8, 20, 30, tzinfo=timezone.utc), '2024-01-31T08:20:30+00:00'),
        (
            datetime(2024, 1, 31, 8, 20, 30, tzinfo=timezone(timedelta(hours=10))),
            '2024-01-31T08:20:30+10:00',
        ),
        (date(2024, 1, 31), '2024-01-31'),
        (time(8, 20, 30), '08:20:30'),
        (time(8, 20, 30, microsecond=123), '08:20:30.000123'),
        (timedelta(hours=10), '36000.0'),
        (timedelta(hours=-10), '-36000.0'),
        (Decimal(123), 123),
        (Decimal(123.0), 123.0),
        (Decimal(123.4), 123.4),
    ],
)
def test_json_default_ok(v, expected):
    assert json_default(v) == expected


class NoStringEquiv:
    """Cannot be converted to str."""

    def __str__(self):
        return None


def test_json_default_bad():
    with pytest.raises(TypeError):
        json_default(NoStringEquiv())


# ------------------------------------------------------------------------------
@pytest.mark.parametrize(
    'd,required,optional,ignore',
    [
        ({'a': 0, 'b': 1, 'x-wotcha': 2}, ['a'], None, None),
        ({'a': 0, 'b': 1, 'x-wotcha': 2}, ['a'], ['b', 'x-wotcha'], None),
        ({'a': 0, 'b': 1, 'x-wotcha': 2}, ['a'], ['b'], 'x-*'),
        ({'a': 0, 'b': 1, 'x-wotcha': 2}, ['a'], ['b'], ['x-*']),
    ],
)
def test_dict_check_ok(d, required, optional, ignore):
    assert dict_check(d, required, optional, ignore) is None


@pytest.mark.parametrize(
    'd,required,optional,ignore',
    [
        ({'a': 0, 'b': 1, 'x-wotcha': 2}, ['a'], ['b'], None),
        ({'a': 0, 'b': 1, 'x-wotcha': 2}, ['a', 'missing'], ['b'], None),
    ],
)
def test_dict_check_bad(d, required, optional, ignore):
    with pytest.raises(ValueError):
        dict_check(d, required, optional, ignore)


# ------------------------------------------------------------------------------
def test_import_by_name():
    m = import_by_name('version', 'lava')
    assert m.version()


# ------------------------------------------------------------------------------
@pytest.mark.parametrize('sep,args,expected', [('/', ('a', [], ['b', 'c']), 'a/b/c')])
def test_sepjoin(sep, args, expected):
    assert sepjoin(sep, *args) == expected


# ------------------------------------------------------------------------------
@pytest.mark.parametrize(
    'path,pathsep,extsep,expected',
    [
        ('a', None, None, ('a', '')),
        ('.a', None, None, ('.a', '')),
        ('a/b/c.gz', None, None, ('a/b/c', '.gz')),
        ('a/b/c.tar.gz', None, None, ('a/b/c', '.tar.gz')),
    ],
)
def test_splitext2(path, pathsep, extsep, expected):
    assert splitext2(path, pathsep or os.sep, extsep or os.extsep) == expected


# ------------------------------------------------------------------------------
@pytest.mark.parametrize(
    'd,expected',
    [
        ({'a': 0}, {'a': 0}),
        ({'a': 0, 'b.c': 1}, {'a': 0, 'b': {'c': 1}}),
    ],
)
def test_expand_keys(d, expected):
    assert dict_expand_keys(d) == expected


def test_expand_keys_conflict():
    with pytest.raises(ValueError, match='Path conflict'):
        dict_expand_keys({'a': 0, 'a.b': 1})


def test_expand_keys_bad_key_type():
    with pytest.raises(ValueError, match='Non string key'):
        dict_expand_keys({99: 0, 'b': 1})


# ------------------------------------------------------------------------------
@pytest.mark.parametrize(
    'd,expected',
    [({'a': 0, 'skip-me': None, 'b': 1}, {'a': 0, 'b': 1})],
)
def test_dist_strip(d, expected):
    assert dict_strip(d) == expected


# ------------------------------------------------------------------------------
@pytest.mark.parametrize(
    'd,keys,v,expected',
    [
        ({}, ('a', 'b'), 22, {'a': {'b': 22}}),
    ],
)
def test_dict_set_deep_ok(d, keys, v, expected):
    dict_set_deep(d, keys, v)
    assert d == expected


@pytest.mark.parametrize(
    'd,keys,v',
    [
        ({'a': 10}, ('a', 'b'), 22),
        ('a', ('a',), 22),
    ],
)
def test_dict_set_deep_bad(d, keys, v):
    with pytest.raises(ValueError):
        dict_set_deep(d, keys, v)


# ------------------------------------------------------------------------------
@pytest.mark.parametrize(
    'd,keys,expected',
    [
        ({'a': 0, 'b': 1}, ['a'], {'a': 0}),
        ({'a': 0, 'b': 1}, {'a'}, {'a': 0}),
    ],
)
def test_dict_select(d, keys, expected):
    assert dict_select(d, *keys) == expected


# ------------------------------------------------------------------------------
@pytest.mark.parametrize(
    'd1, d2, ignore, isequal',
    [
        (
            {'a': 'A', 'b': 2, 'c': True, 'd': [1, 2, 3]},
            {'a': 'A', 'b': 2, 'c': True, 'd': [1, 2, 3]},
            None,
            True,
        ),
        (
            {'a': 'A', 'b': 2, 'c': True, 'd': [1, 2, 3]},
            {'b': 2, 'a': 'A', 'c': True, 'd': [1, 2, 3]},
            None,
            True,
        ),
        (
            {'a': 'A', 'b': 2, 'c': True, 'd': [1, 2, 3]},
            {'a': 'A', 'b': 2, 'c': False, 'd': [1, 2, 3]},
            'c*',
            True,
        ),
        (
            {'a': 'A', 'b': 2, 'c': True, 'd': [1, 2, 3]},
            {'a': 'A', 'b': 2, 'c': False, 'd': 'excluded'},
            '[cd]*',
            True,
        ),
        (
            {'a': 'A', 'b': 2, 'c': True, 'd': [1, 2, 3]},
            {'a': 'A', 'b': 2, 'c': False, 'd': 'excluded'},
            ['c', 'd*'],
            True,
        ),
        (
            {'a': 'A', 'b': 2, 'c': True, 'd': [1, 2, 3]},
            {'a': 'A', 'b': 2, 'c': False, 'd': 'excluded'},
            None,
            False,
        ),
    ],
)
def test_dict_hash(d1: dict, d2: dict, ignore, isequal: bool):
    assert (dict_hash(d1, ignore) == dict_hash(d2, ignore)) == isequal


# ------------------------------------------------------------------------------
@pytest.mark.parametrize(
    's,expected',
    [
        ('yes', True),
        ('y', True),
        ('t', True),
        ('trUE', True),
        ('1', True),
        ('no', False),
        ('N', False),
        ('f', False),
        ('FALSE', False),
        ('0', False),
    ],
)
def test_str2bool_ok(s, expected):
    assert str2bool(s) == expected


@pytest.mark.parametrize(
    's,exc',
    [
        (21, TypeError),
        ([], TypeError),
        ('no-idea', ValueError),
    ],
)
def test_str2bool_fail(s, exc):
    with pytest.raises(exc):
        str2bool(s)


# ------------------------------------------------------------------------------
@pytest.mark.parametrize(
    's,quote,expected',
    [
        ('nope', "'", False),
        ('"nope', '"', False),
        ('"yep"', '"', True),
    ],
)
def test_is_quoted(s, quote, expected):
    assert is_quoted(s, quote) == expected


# ------------------------------------------------------------------------------
@pytest.mark.parametrize(
    'v,expected',
    [
        ([1, 2, 3], [1, 2, 3]),
        ('abc', ['abc']),
        ({'a': 0, 'b': 1}, ['a', 'b']),
    ],
)
def test_listify(v, expected):
    assert listify(v) == expected


# ------------------------------------------------------------------------------
@pytest.mark.parametrize(
    's,expected',
    [
        ('<HTML>blah blah', True),
        ('<!DOCTYPE html ...', True),
        ('   <!DOCTYPE html ...', True),
        ('nope', False),
    ],
)
def test_is_html(s, expected):
    assert is_html(s) is expected


# ------------------------------------------------------------------------------
@pytest.mark.parametrize(
    's,safe_chars,alternative,expected',
    [
        ('a', 'a', 'a', 'a'),
        ('a/b', None, None, 'ab'),
        ('a/b', None, '.', 'a.b'),
        ('a////b', None, '.', 'a.b'),
        ('a/b', '/', '.', 'a/b'),
        ('/a/b', '/', '.', 'a/b'),  # Safe chars can't start/end the string
    ],
)
def test_clean_str_ok(s, safe_chars, alternative, expected):
    assert clean_str(s, safe_chars, alternative) == expected


@pytest.mark.parametrize(
    's,safe_chars,alternative,error',
    [
        ('', None, None, 'Empty string'),
        ('//.', None, None, 'Result is empty'),
        ('a', None, 'too-long', 'Alternative must be a single character'),
    ],
)
def test_clean_str_fail(s, safe_chars, alternative, error):
    with pytest.raises(ValueError, match=error):
        clean_str(s, safe_chars, alternative)


# ------------------------------------------------------------------------------
@pytest.mark.parametrize(
    'd,expected', [(Decimal(123), (int, 123)), (Decimal(123.4), (float, 123.4))]
)
def test_decimal_to_scalar(d, expected: tuple):
    assert (v := decimal_to_scalar(d)) == expected[1] and isinstance(v, expected[0])


# ------------------------------------------------------------------------------
@pytest.mark.parametrize(
    's, globs, ignore_case, expected',
    [
        ('x-abc', ['x-', 'abc'], False, False),
        ('x-abc', ['x-*', 'abc'], False, True),
        ('x-abc', ['X-*', 'abc'], False, False),
        ('x-abc', ['X-*', 'abc'], True, True),
    ],
)
def test_match_any(s, globs, ignore_case, expected):
    assert match_any(s, globs, ignore_case) == expected
    assert match_none(s, globs, ignore_case) == (not expected)


# ------------------------------------------------------------------------------
def test_defer():

    def exclaim(*s):
        """Return a string with an exclamation mark on the end."""
        return ' '.join(s) + '!'

    def div(n, m):
        """Divide two numbers."""
        return n / m

    d = Defer.on_event('test')
    # Make sure its asingleton per event type
    assert d is Defer.on_event('test')

    d.add(Task('First in', exclaim, ['hello', 'world']))
    assert d.tasks[1].description == 'First in'

    # Test cancelling a task
    task_id = d.add(Task('Cancel this one', exclaim, ['goodbye', 'world']))
    assert len(d.tasks) == 2
    d.cancel(task_id)
    assert len(d.tasks) == 1
    assert d.tasks[1].description == 'First in'

    # Add another task that will succeed
    d.add(Task('Last in', exclaim, ['abra', 'cadabra']))

    # Add a task that will fail with an exception
    d.add(Task('Div by zero', div, kwargs={'n': 1, 'm': 0}))

    # Run our tasks in LIFO
    results = d.run(logger=logging.getLogger())
    assert isinstance(results[0].exception, ZeroDivisionError)
    assert results[1].result == 'abra cadabra!'
    assert results[2].result == 'hello world!'


# ------------------------------------------------------------------------------
@pytest.mark.parametrize(
    'd1,d2,ignore,expected',
    [
        ({'a': 1, 'b': 'B', 'c': [1, 'C']}, {'a': 1, 'b': 'B', 'c': [1, 'C']}, None, True),
        ({'a': 1, 'b': 'B', 'c': [1, 'C']}, {'a': 1, 'b': 'B', 'c': ['C', 1]}, None, False),
        ({'a': 1, 'b': 'B', 'x-c': [1, 'C']}, {'a': 1, 'b': 'B', 'x-d': [1, 'D']}, 'x-*', True),
        ({'a': 1, 'b': 'B', 'x-c': [1, 'C']}, {'a': 1, 'b': 'B', 'x-d': [1, 'D']}, ['x-*'], True),
    ],
)
def test_dictchecksum_ok(d1, d2, ignore, expected):
    ds1 = DictChecksum.for_dict(d1, ignore=ignore)
    ds2 = DictChecksum.for_dict(d2, ignore=ignore)
    assert (ds1 == ds2) == expected

    ds10 = DictChecksum.from_str(str(ds1))
    assert (ds10 == ds2) == expected

    assert ds10.is_valid_for(d1, ignore=ignore)


@pytest.mark.parametrize(
    'd,version,error,message',
    [
        ('bad-type', CHECKSUM_DEFAULT_VERSION, TypeError, 'requires dict'),
        ({}, -1, ValueError, 'checksum format version'),
    ],
)
def test_dictchecksum_for_dict_fail(d, version, error, message):
    with pytest.raises(error, match=message):
        DictChecksum.for_dict(d, version=version)  # noqa


@pytest.mark.parametrize(
    's,error,message',
    [
        ('woof', ValueError, 'Malformed checksum'),
        ('version;sha256;c;d', ValueError, 'invalid literal for int'),
        (f'{CHECKSUM_DEFAULT_VERSION};bad-algorithm;c;d', ValueError, 'Algorithm must be one of'),
    ],
)
def test_dictchecksum_from_str_fail(s, error, message):
    with pytest.raises(error, match=message):
        DictChecksum.from_str(s)


# ------------------------------------------------------------------------------
def test_tracked_mapping():

    data = {'a': 'A', 'b': 'B'}
    tm = TrackedMapping(data)

    assert str(data) == str(tm)
    assert f'({data!r})' in repr(tm)

    assert len(tm.unknown_refs) == 0
    assert len(tm.unknown_refs) == 0
    assert len(tm) == len(data)

    for k, v in tm.items():
        assert tm[k] == v
        assert tm.get(k) == v
    assert set(data) == tm.visited_refs

    with pytest.raises(KeyError):
        _ = tm['no-such-key']
    assert 'no-such-key' in tm.unknown_refs

    with pytest.raises(KeyError):
        del tm['no-such-key']

    # Mutations ...
    del tm['a']
    assert 'a' not in tm

    tm['x'] = 'X'
    assert tm['x'] == 'X'
    assert 'x' in tm.visited_refs

    # Try one with a default_factory
    tm = TrackedMapping(data, int)
    assert tm['a'] == 'A'
    assert tm['nope'] == 0
    assert 'nope' in tm.unknown_refs
    assert 'nope' in tm.visited_refs


# ------------------------------------------------------------------------------
@pytest.mark.parametrize(
    'seq, expected',
    [
        (tuple(), '()'),
        ([], '[]'),
        (
            ('a', 99, True),
            """
(
    a,
    99,
    True
)
""",
        ),
        (
            ['a', 99, False],
            """
[
    a,
    99,
    False
]
""",
        ),
        (
            ['a', 99, {'b': 'B'}],
            """
[
    a,
    99,
    {
        'b': B
    }
]
    """,
        ),
    ],
)
def test_format_sequence_unescaped(seq, expected):
    assert format_sequence_unescaped(seq) == expected.strip()


# # ------------------------------------------------------------------------------
@pytest.mark.parametrize(
    'd, expected',
    [
        ({}, '{}'),
        (
            {'a': 'A', 'b': 99, 'c': True},
            """
{
    'a': A,
    'b': 99,
    'c': True
}
""",
        ),
        (
            {'a': 'A', 'b': {'bb': 'BB'}, 'c': ['C', 33]},
            """
{
    'a': A,
    'b': {
        'bb': BB
    },
    'c': [
        C,
        33
    ]
}
""",
        ),
        ('A', "'A'"),
        (9, '9'),
    ],
)
def test_format_dict_escaped(d, expected):
    assert format_dict_unescaped(d) == expected.strip()
