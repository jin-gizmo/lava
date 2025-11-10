"""OS related utilities."""

from __future__ import annotations

import errno
import os
import signal

from .decorators import deprecated

__author__ = 'Murray Andrews'

# map signal numbers to names
signal_names = {
    getattr(signal, name): name
    for name in dir(signal)
    if name.startswith('SIG') and not name.startswith('SIG_')
}


# ------------------------------------------------------------------------------
def signum(sig: str | int) -> int:
    """
    Convert a signal name to the corresponding signal number.

    e.g `SIGINT` or `INT` --> 2.

    :param sig:         Either a signal name or a signal number. If the latter
                        it is checked for validity and returned unchanged if
                        valid.

    :return:            The signal number.

    :raise ValueError:  If the signal is not known.

    """

    if isinstance(sig, int):
        if sig not in signal_names:
            raise ValueError(f'Unknown signal: {sig}')
        return sig

    sig_num = getattr(signal, sig.upper(), getattr(signal, 'SIG' + sig.upper(), None))
    if not sig_num:
        raise ValueError(f'Unknown signal: {sig}')

    return sig_num


# ------------------------------------------------------------------------------
def signame(sig: str | int) -> str:
    """
    Convert a signal to the corresponding name.

    :param sig:         Either a signal number of name. If the latter it is
                        converted to its cannonical form (ie. SIGINT not INT).

    :return:            The signal name.

    :raise ValueError:  If the signal is not known.

    """

    if isinstance(sig, int):
        if sig in signal_names:
            return signal_names[sig]
        raise ValueError(f'Unknown signal: {sig}')

    # String signal name.
    return signal_names[signum(sig)]


# ------------------------------------------------------------------------------
@deprecated('Just use os.makedirs() instead')
def makedirs(path: str, mode: int = 0o777, exist_ok: bool = False) -> None:
    """
    Create directories.

    !!! warning "Deprecated as of v8.1.0"
        Just use os.makedirs() instead.

    Repackaging of os.makedirs() to ignore file exists error.

    This is required due to a bug in os.makedirs() in Python 3.4.0 which is
    fixed in 3.4.1.

    See https://bugs.python.org/issue13498
    and  https://bugs.python.org/issue21082

    :param path:        As for os.makedirs()
    :param mode:        As for os.makedirs()
    :param exist_ok:    As for os.makedirs()

    :return:
    """

    try:
        os.makedirs(path, mode, exist_ok)
    except OSError as e:
        # Ignore file exists error.
        if not exist_ok or e.errno != errno.EEXIST:
            raise
