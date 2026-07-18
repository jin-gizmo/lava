"""Test lava datetime utils."""

import pytest

from lava.lib.datetime import *


# ------------------------------------------------------------------------------
@pytest.mark.parametrize(
    's,result',
    [
        (30, 30),
        (30.5, 30.5),
        ('1', 1),
        ('10.5', 10.5),
        ('-10.5', -10.5),
        ('1s', 1),
        ('2m', 2 * 60),
        ('-21m', -21 * 60),
        ('20.5m', 20.5 * 60),
        ('2h', 2 * 60 * 60),
        ('+2h', 2 * 60 * 60),
        ('-2h', -2 * 60 * 60),
        ('-2.5h', -2.5 * 60 * 60),
        ('23d', 23 * 24 * 60 * 60),
        ('-23.5d', -23.5 * 24 * 60 * 60),
        ('4w', 4 * 7 * 24 * 60 * 60),
        ('4.5w', 4.5 * 7 * 24 * 60 * 60),
    ],
)
def test_duration_to_seconds_ok(s, result):
    assert duration_to_seconds(s) == result


@pytest.mark.parametrize(
    's',
    [
        'bad',
        ['No', 'lists', 'pls'],
    ],
)
def test_duration_to_seconds_bad(s):
    with pytest.raises(ValueError):
        duration_to_seconds(s)


# ------------------------------------------------------------------------------
@pytest.mark.parametrize(
    't,result',
    [
        (datetime.time(12, 30, 40), '12:30:40.000000'),
        (datetime.time(2, 15, 35, microsecond=123456), '02:15:35.123456'),
    ],
)
def test_time_to_str_ok(t, result):
    assert time_to_str(t) == result


# ------------------------------------------------------------------------------
@pytest.mark.parametrize(
    't',
    ['Must be a datetime.time()'],
)
def test_time_to_str_bad(t):
    with pytest.raises(ValueError):
        time_to_str(t)  # noqa


# ------------------------------------------------------------------------------
@pytest.mark.parametrize(
    't,result',
    [
        (datetime.timedelta(minutes=30), str(30 * 60.0)),
    ],
)
def test_timedelta_to_str_ok(t, result):
    assert timedelta_to_str(t) == result


# ------------------------------------------------------------------------------
@pytest.mark.parametrize(
    'td',
    ['Must be a datetime.timedelta()'],
)
def test_timedelta_to_str_bad(td):
    with pytest.raises(ValueError):
        timedelta_to_str(td)  # noqa


# ------------------------------------------------------------------------------
@pytest.mark.parametrize(
    'td,result',
    [
        (datetime.timedelta(minutes=30), (0, 30, 0)),
        (datetime.timedelta(hours=3, minutes=30, seconds=45), (3, 30, 45)),
        # Seconds round up
        (datetime.timedelta(hours=3, minutes=30, seconds=45.3), (3, 30, 45)),
        (datetime.timedelta(hours=3, minutes=30, seconds=45.5), (3, 30, 46)),
    ],
)
def test_time_to_hms(td, result):
    assert timedelta_to_hms(td) == result


# ------------------------------------------------------------------------------
def test_timestamp():
    """Test timestamp() - not much needed here."""
    ts_pair = timestamp()
    assert len(ts_pair) == 2 and [datetime.datetime.fromisoformat(ts) for ts in ts_pair]


# ------------------------------------------------------------------------------
def test_nowtz():
    """Test nowtz() - not much needed here."""
    now = now_tz()
    assert isinstance(now, datetime.datetime) and now.utcoffset() is not None


# ------------------------------------------------------------------------------
@pytest.mark.parametrize(
    's,result',
    [
        (
            '2024-04-26T07:18:19Z',
            datetime.datetime(2024, 4, 26, 7, 18, 19, tzinfo=datetime.timezone.utc),
        ),
        (
            '2024-04-26T07:18:19+00:00',
            datetime.datetime(2024, 4, 26, 7, 18, 19, tzinfo=datetime.timezone.utc),
        ),
        (
            '2024-04-26T17:18:19+10:00',
            datetime.datetime(2024, 4, 26, 7, 18, 19, tzinfo=datetime.timezone.utc),
        ),
        (
            '2024-04-26T17:18:19+10:00',
            datetime.datetime(
                2024, 4, 26, 17, 18, 19, tzinfo=datetime.timezone(datetime.timedelta(hours=10))
            ),
        ),
    ],
)
def test_parse_dt(s, result):
    assert parse_dt(s) == result
