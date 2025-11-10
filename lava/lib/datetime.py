"""Date/time utilities."""

from __future__ import annotations

import datetime
import re
import time
from decimal import Decimal

import dateutil.parser
import dateutil.tz

from .decorators import deprecated

__author__ = 'Murray Andrews'

DT_MIN = datetime.datetime(year=datetime.MINYEAR, month=1, day=1).replace(tzinfo=dateutil.tz.UTC)
DT_MAX = datetime.datetime(year=datetime.MAXYEAR, month=12, day=31).replace(tzinfo=dateutil.tz.UTC)

# ------------------------------------------------------------------------------
TIME_UNITS = {
    'w': 60 * 60 * 24 * 7,
    'd': 60 * 60 * 24,
    'h': 60 * 60,
    'm': 60,
    's': 1,
    '': 1,  # Default is seconds
}

DURATION_REGEX = (
    r'\s*((?P<value>[+-]?(\d+(\.\d*)?|\.\d+)([eE][+-]?\d+)?)\s*'
    r'(?P<units>[{units}]?))\s*$'.format(units=''.join(TIME_UNITS.keys()))
)


def duration_to_seconds(duration: str | int | float | Decimal) -> float:
    """
    Convert a string specifying a time duration to a number of seconds.

    :param duration:    String in the form nnnX where nnn is an integer or float
                        and X is one of (case sensitive):
                        'w':    weeks
                        'd':    days
                        'h':    hours
                        'm':    minutes
                        's':    seconds.

                        If X is missing then seconds are assumed. Whitespace is ignored.
                        Can also be a float or integer. Note a leading + or - will be
                        handled correctly as will exponentials.

    :return:            The duration in seconds.

    :raise ValueError:  If the duration is malformed.

    """

    if isinstance(duration, (int, float, Decimal)):
        return float(duration)

    if not isinstance(duration, str):
        raise ValueError(f'Invalid duration type: {type(duration)}')

    m = re.match(DURATION_REGEX, duration)

    if not m:
        raise ValueError('Invalid duration: ' + duration)

    return float(m.group('value')) * TIME_UNITS[m.group('units')]


# ------------------------------------------------------------------------------
@deprecated('Just use str(t) instead')
def time_to_str(t: datetime.time) -> str:
    """
    Convert a time object to a string suitable for use in API responses.

    !!! warning "Deprecated as of v8.0.0"
        Just use str(t) instead.

    :param t:       A time object

    :return:        A string representation of the time

    :raise ValueError: If the object is not a time object.

    """

    if not isinstance(t, datetime.time):
        raise ValueError(f'Expected time not {type(t)}')

    return t.strftime('%H:%M:%S.%f')


# ------------------------------------------------------------------------------
def timedelta_to_str(delta: datetime.timedelta) -> str:
    """
    Convert a timedelta instance to a string.

    :param delta:   A timedelta object.

    :return:        A string representation of the timedelta.

    """

    if not isinstance(delta, datetime.timedelta):
        raise ValueError(f'Expected timedelta not {type(delta)}')

    return str(delta.total_seconds())


# ------------------------------------------------------------------------------
def timedelta_to_hms(td: datetime.timedelta) -> tuple[int, int, int]:
    """
    Convert a timedelta to hours, minutes, seconds (rounded to nearest second).

    Results may not be quite what you expect if td is negative.

    :param td:      A timedelta

    :return:        A triple (hours, minutes, seconds)

    """

    totalsecs = int(round(td.total_seconds(), 0))
    hours = totalsecs // 3600
    minutes = (totalsecs - 3600 * hours) // 60
    seconds = totalsecs - 3600 * hours - 60 * minutes

    return hours, minutes, seconds


# ------------------------------------------------------------------------------
def timestamp() -> tuple[str, str]:
    """
    Return the current UTC and localtime as a pair of ISO8601 strings.

    Precision is to the nearest second.

    :return:        A tuple of strings: UTC-time, Local-time

    """

    ts = round(time.time())

    t_local = datetime.datetime.fromtimestamp(ts).isoformat()
    t_utc = datetime.datetime.utcfromtimestamp(ts).isoformat()

    return t_utc, t_local


# ------------------------------------------------------------------------------
def now_tz() -> datetime.datetime:
    """
    Get the current time as a timezone aware time.

    :return:        Return the current time as a timezone aware time rounded
                    down to the nearest second.

    """

    return datetime.datetime.now(dateutil.tz.tzlocal()).replace(microsecond=0)


# ------------------------------------------------------------------------------
def parse_dt(s: str) -> datetime.datetime:
    """
    Parse a datetime string and ensure it has a timezone.

    If one is not yielded by the parsing then the local timezone will be added.

    :param s:       A string representing a date time.

    :return:        Timezone aware datetime.

    """

    dt = dateutil.parser.parse(s)

    return dt if dt.tzinfo else dt.replace(tzinfo=dateutil.tz.tzlocal())
