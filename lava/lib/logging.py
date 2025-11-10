"""Logging utilities."""

from __future__ import annotations

import json
import logging
import os
import stat
import sys
import time
from datetime import datetime, timezone
from logging.handlers import SysLogHandler

from .misc import json_default

__author__ = 'Murray Andrews'


# -------------------------------------------------------------------------------
def syslog_address() -> str | tuple:
    """
    Try to work out the syslog address.

    :return:    A value suitable for use as the address arg for SysLogHandler.
    """

    for f in ('/dev/log', '/var/run/syslog'):
        try:
            mode = os.stat(f).st_mode
        except OSError:
            continue

        if stat.S_ISSOCK(mode):
            return f

    return 'localhost', 514


# -------------------------------------------------------------------------------
def get_log_level(s: str) -> int:
    """
    Convert string log level to the corresponding integer log level.

    Raises ValueError if a bad string is provided.

    :param s:       A string version of a log level (e.g. 'error', 'info').
                    Case is not significant.

    :return:        The numeric logLevel equivalent.

    :raise ValueError: If the supplied string cannot be converted.
    """

    if not s or not isinstance(s, str):
        raise ValueError('Bad log level:' + str(s))

    t = s.upper()

    if not hasattr(logging, t):
        raise ValueError('Bad log level: ' + s)

    return getattr(logging, t)


# ..............................................................................
# region colour

# ------------------------------------------------------------------------------
# Clunky support for colour output if colorama is not installed.


try:
    # noinspection PyUnresolvedReferences
    import colorama

    # noinspection PyUnresolvedReferences
    from colorama import Fore, Style

    colorama.init()

except ImportError:

    class Fore:
        """Basic alternative to colorama colours using ANSI sequences."""

        RESET = '\033[0m'
        BLACK = '\033[30m'
        RED = '\033[31m'
        GREEN = '\033[32m'
        YELLOW = '\033[33m'
        BLUE = '\033[34m'
        MAGENTA = '\033[35m'
        CYAN = '\033[36m'

    class Style:
        """Basic alternative to colorama styles using ANSI sequences."""

        RESET_ALL = '\033[0m'
        BRIGHT = '\033[1m'
        DIM = '\033[2m'
        NORMAL = '\033[22m'


# endregion colour
# ..............................................................................


# ------------------------------------------------------------------------------
class ColourLogHandler(logging.Handler):
    """Basic stream handler that writes to stderr with colours for log levels."""

    # --------------------------------------------------------------------------
    def __init__(self, colour: bool = True):
        """
        Allow colour to be enabled or disabled.

        :param colour:      If True colour is enabled for log messages.
                            Default True.

        """

        super().__init__()
        self.colour = colour

    # --------------------------------------------------------------------------
    def emit(self, record: logging.LogRecord) -> None:
        """
        Print the record to stderr with some colour enhancement.

        :param record:  Log record
        """

        if self.colour:
            if record.levelno >= logging.ERROR:
                colour = Style.BRIGHT + Fore.RED
            elif record.levelno >= logging.WARNING:
                colour = Fore.MAGENTA
            elif record.levelno >= logging.INFO:
                colour = Fore.BLUE
            else:
                colour = Style.DIM + Fore.BLACK

            print(colour + self.format(record) + Fore.RESET + Style.RESET_ALL, file=sys.stderr)
        else:
            print(self.format(record), file=sys.stderr)


# ------------------------------------------------------------------------------
class JsonFormatter(logging.Formatter):
    """
    Format log records in JSON format.

    Thanks to: https://www.velebit.ai/blog/tech-blog-python-json-logging/

    :param  fields:     A dictionary of fields to use in the log. Keys will be
                        used in the final log record. Values are the names of
                        the attributes from the log record.  values.
    :param extra:       Additional fields to add to all records.
    :param datefmt:     As per logging.Formatter.
    :param tag:         Preceed the JSON encode log record with `{tag}: `.
                        This is very important when logging to rsyslog as this
                        provides the value of the rsyslog `syslogtag`. If not
                        specified, rsyslog will try to inseet `[pid]` before the
                        first space in the JSON blob, which will wreck the JSON.
                        When just logging to a file, this parameter will
                        generally be None to produce a well-formed JSON blob for
                        each line.
    """

    LOG_RECORD_ATTRIBUTES = frozenset(
        {
            'args',
            'asctime',
            'created',
            'exc_info',
            'exc_text',
            'filename',
            'funcName',
            'isotime',  # This is a custom addition
            'levelname',
            'levelno',
            'lineno',
            'module',
            'msecs',
            'message',
            'msg',
            'name',
            'pathname',
            'process',
            'processName',
            'relativeCreated',
            'stack_info',
            'thread',
            'threadName',
        }
    )

    # --------------------------------------------------------------------------
    def __init__(
        self,
        fields: dict[str, str] = None,
        extra: dict[str, str] = None,
        datefmt: str = None,
        tag: str = None,
    ):
        """Create a JSON formatter."""

        super().__init__(fmt=None, datefmt=datefmt, style='%')
        self.fields = fields or {}
        self._uses_time = 'asctime' in self.fields.values()
        self.extra = {k: v for k, v in extra.items() if v} if extra else {}
        self.default_msec_format = None  # Disable milliseconds
        self.tag = tag

    # --------------------------------------------------------------------------
    def formatTime(self, record, datefmt=None):  # noqa: N802
        """
        Return the creation time of the specified LogRecord as formatted text.

        This is basically the Python 3.9 standard implementation. It is included
        here to compensate for an issue with the Python 3.8 version that barfs
        if default_msec_fmt is set to None.
        """

        ct = self.converter(record.created)
        if datefmt:
            s = time.strftime(datefmt, ct)
        else:
            s = time.strftime(self.default_time_format, ct)
            if self.default_msec_format:
                s = self.default_msec_format % (s, record.msecs)
        return s

    # --------------------------------------------------------------------------
    @staticmethod
    def isotime(record):
        """Return the creation time as a precise ISO 8601 string in UTC."""

        return (
            datetime.utcfromtimestamp(record.created)
            .replace(tzinfo=timezone.utc)
            .isoformat(timespec='microseconds')
        )

    # --------------------------------------------------------------------------
    def usesTime(self):  # noqa N802
        """Check if the format uses the creation time of the record."""

        return self._uses_time

    # --------------------------------------------------------------------------
    def format(self, record: logging.LogRecord) -> str:  # noqa A003
        """Format a log record as JSON."""

        data = self.extra.copy()
        record.message = record.getMessage()

        if self.usesTime():
            record.asctime = self.formatTime(record, self.datefmt)
            # This is a custom addition
            record.isotime = self.isotime(record)
        if record.exc_info and record.exc_text:
            record.exc_text = self.formatException(record.exc_info)
        record.stack_info = self.formatStack(record.stack_info)

        # extract wanted fields from log record
        for key, field in self.fields.items():
            value = record.__dict__.get(field, None)
            if field == 'exc_info':
                value = record.exc_text
            if value:
                data[key] = value

        # copy only LogRecord extra
        for field, value in record.__dict__.items():
            # skip all standard fields and internal variables
            if field in self.LOG_RECORD_ATTRIBUTES or field.startswith('_'):
                continue
            data[field] = value

        # noinspection PyBroadException
        try:
            jrec = json.dumps(data, default=json_default)
        except Exception as e:
            # Uh oh. This is bad but we don't want an entire thread to die.
            # Give up but don't crash. Assume the extras are safe.
            data = self.extra.copy()
            data['internal_error'] = str(e)
            jrec = json.dumps(data, default=json_default)

        return f'{self.tag}: {jrec}' if self.tag else jrec


# ------------------------------------------------------------------------------
def setup_logging(
    level: str,
    target: str = None,
    colour: bool = True,
    name: str = None,
    prefix: str = None,
    formatter: logging.Formatter = None,
) -> None:
    """
    Set up logging.

    :param level:   Logging level. The string format of a level (eg 'debug').
    :param target:  Logging target. Either a file name or a syslog facility name
                    starting with @ or None. If None, log to stderr.
    :param colour:  If True and logging to the terminal, colourise messages for
                    different logging levels. Default True.
    :param name:    The name of the logger to configure. If None, configure the
                    root logger.
    :param prefix:  Messages are prefixed by this string (with colon+space
                    appended). Defaults to None but it is important this is set
                    when logging to rsyslog otherwise syslog may mangle the
                    message.
    :param formatter: Use the specified logging formatter instead of the default.
                    The default varies a bit depending on log target.

    :raise ValueError: If an invalid log level or syslog facility is specified.
    """

    logger = logging.getLogger(name)
    logger.propagate = False
    logger.setLevel(get_log_level(level))

    # Get rid of unwanted handlers.
    for h in logger.handlers:
        logger.removeHandler(h)

    if target:
        if target.startswith('@'):
            # Syslog to specified facility

            if target[1:] not in SysLogHandler.facility_names:
                raise ValueError(f'Bad syslog facility: {target[1:]}')
            # SysLogHandler does accept string facility names
            # noinspection PyTypeChecker
            h = SysLogHandler(address=syslog_address(), facility=target[1:])
            h.setFormatter(
                formatter
                or logging.Formatter(
                    (prefix if prefix else '')
                    + '[%(process)d]: %(levelname)s: %(threadName)s: %(message)s'
                )
            )
        else:
            # Log to a file
            h = logging.FileHandler(target)
            h.setFormatter(
                formatter
                or logging.Formatter('%(asctime)s: %(levelname)s: %(threadName)s: %(message)s')
            )
        logger.addHandler(h)
        logger.debug('%s', ' '.join(sys.argv))
        logger.debug('Logfile set to %s', target)
    else:
        # Just log to stderr.
        h = ColourLogHandler(colour=colour)
        h.setFormatter(
            formatter
            or logging.Formatter((prefix + ': ' if prefix else '') + '%(threadName)s: %(message)s')
        )
        logger.addHandler(h)
    logger.debug('Log level set to %s (%d)', level, logger.getEffectiveLevel())
