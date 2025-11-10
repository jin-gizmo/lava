"""Make the current process run as a daemon."""

from __future__ import annotations

import fcntl
import os
import resource
import signal
import sys
from grp import getgrnam
from pwd import getpwnam
from typing import Any

from .os import signum

__author__ = 'Murray Andrews'

FD_MAX = 1024  # Maximum # of file descriptors to close

_SIGNAL_DEFAULTS = {
    'SIGHUP': signal.SIG_IGN,
    'SIGINT': signal.SIG_IGN,
    'SIGTSTP': signal.SIG_IGN,
    'SIGTTIN': signal.SIG_IGN,
    'SIGTTOU': signal.SIG_IGN,
}

_PRESERVE_FD_DEFAULT = ['/dev/urandom', '/dev/random']
_lock_fp = None


# ------------------------------------------------------------------------------
def lock_file(fname: str) -> bool:
    """
    Create a lock file with the given name and write the current process PID in it.

    :param fname:       Name of lockfile

    :return:            True if lockfile created, False otherwise.

    :raise Exception:   If the lock file cannot be created.
    """

    global _lock_fp  # Has to stay in scope to stay open

    # Open as append so we don't obliterate PID of another process.
    _lock_fp = open(fname, 'a')  # noqa: SIM115

    try:
        fcntl.lockf(_lock_fp, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError:
        return False

    # Now we have the lock - get rid of old PID contents.
    _lock_fp.truncate(0)

    print(os.getpid(), file=_lock_fp)
    _lock_fp.flush()
    return True


# ------------------------------------------------------------------------------
def set_signal(sig: str | int, handler=None) -> None:
    """
    Set the named signal (SIGHUP) to the specified handler.

    If the named signal does not exist on the system then an exception is
    raised. This can only be called from the main thread or a ValueError
    exception occurs.

    :param sig:         The number or name of the signal (as per signal(2)).
                        e.g. SIGHUP or HUP
    :param handler:     A signal handler. It may be either either None (meaning
                        ignore the signal), signal.SIG_IGN to ignore the signal,
                        signal.SIG_DFL to restore the default or a signal
                        handler function - which must take the two arguments
                        required by handlers by signal.signal() ie. the signal
                        number and the current stack frame. Default None.

    :raise ValueError:  If the signal name is not known on this system or the
                        handler is not None, SIG_IGN, SIG_DFL or a callable.
    :raise Exception:   If something else goes wrong.

    """

    if not handler:
        handler = signal.SIG_IGN
    if handler not in (signal.SIG_IGN, signal.SIG_DFL) and not callable(handler):
        raise ValueError(f'Bad handler for signal: {sig}')

    signal.signal(signum(sig), handler)  # Exceptions can propagate


# ------------------------------------------------------------------------------
def stop_core_dumps() -> None:
    """Prevent core dumps."""

    resource.setrlimit(resource.RLIMIT_CORE, (0, 0))


# ------------------------------------------------------------------------------
# noinspection PyUnusedLocal
def daemonify(  # noqa: C901
    chroot_dir: str = None,
    working_dir: str = None,
    umask: str | int = None,
    uid: str | int = None,
    gid: str | int = None,
    close_fds: bool = True,
    pidfile: str = None,
    stdout: str = None,
    stderr: str = None,
    signals: dict[str, Any] = None,
    preserve_fds: list[str | int] = None,
    **kwargs: Any,
) -> None:
    """
    Convert the current process into a daemon.

    All params are optional. Any unrecognised kwargs are silently ignored.

    :param chroot_dir:  chroot to this directory. Optional. Not tested.
    :param working_dir: cd to this directory. Optional
    :param umask:       Set umask. Must be an int or an octal formatted numeric
                        string. Optional.
    :param uid:         Set uid to this. Can be a user name or a numeric id.
                        Optional. If not specified use real uid.
    :param gid:         Set gid to this. Can be a group name or a numeric id.
                        Optional. If not specified use real uid.
    :param close_fds:   If True close all open file descriptors in the child
                        and reconnect stdin/stdout/stderr to /dev/null. See
                        also the stdout/stderr params which allow these to be
                        sent to a file instead. Default True.
    :param pidfile:     Name of file in which to write the PID. This is also a
                        basic locking mechanism to prevent multiple daemons.
                        Optional.
    :param stdout:      Redirect stdout to the specified file. {pid} will be
                        replaced with the pid. If not specified use /dev/null.
                        Will replace any previous file with same name.
    :param stderr:      Redirect stdout to the specified file. {pid} will be
                        replaced with the pid. If not specified use /dev/null.
                        Will replace any previous file with same name.
    :param signals:     A dictionary. Keys are signal names (e.g. 'SIGHUP')
                        and values are either None (meaning ignore the signal)
                        or a signal handler function - which must take the
                        two arguments required of handlers by signal.signal()
                        ie. the signal number and the current stack frame.
    :param preserve_fds: A list of any file descriptors that should not be
                        closed. The entries in the list can either be numeric
                        (i.e. file descriptors) or filenames. If any of these
                        are already open they will be left open. Any entries
                        that don't correspond to an open file will be silently
                        ignored. There is a bug in Python 3.4.0 (supposedly
                        fixed in 3.4.1) which causes random.urandom() to
                        fail if the file descriptor to /dev/urandom is closed.
                        So if None is specified for preserve_fds, the fds for
                        /dev/urandom and /dev/random will be preserved. If you
                        really don't want that behaviour, provide an empty list
                        as the argument but beware of "bad file descriptor"
                        exceptions in unusual places.
    :param kwargs:      Any left over named args are ignored.

    :raise Exception:   If something goes wrong.

    """

    stop_core_dumps()

    # ---------------------------------------
    # Fork - the first time
    try:
        pid = os.fork()
    except OSError as e:
        raise Exception(f'Cannot fork (1): {e}')

    if pid:
        # Parent can exit now. _exit() is the recommended approach.
        # noinspection PyProtectedMember,PyUnresolvedReferences
        os._exit(0)  # noqa: SLF001

    # noinspection PyArgumentList
    os.setsid()

    # ---------------------------------------
    # Fork - the second time (to prevent zombies)
    try:
        pid = os.fork()
    except OSError as e:
        raise Exception(f'Cannot fork (2): {e}')

    if pid:
        # First child can exit now. _exit() is the recommended approach.
        # noinspection PyProtectedMember,PyUnresolvedReferences
        os._exit(0)  # noqa: SLF001

    # ---------------------------------------
    # Grandchild continues

    # ---------------------------------------
    # Chroot - not tested.
    if chroot_dir:
        if os.geteuid() != 0:
            raise Exception(f'Cannot chroot to {chroot_dir}: you are not root')

        try:
            os.chroot(chroot_dir)
        except Exception as e:
            raise Exception(f'Cannot chroot to {chroot_dir}: {e}')

    # ---------------------------------------
    # Set uid and gid
    if gid is not None:
        if isinstance(gid, str):
            try:
                gid = getgrnam(gid).gr_gid
            except KeyError:
                # No group with this name. Maybe its an int.
                try:
                    gid = int(gid)
                except ValueError:
                    # Nope not an int either.
                    raise Exception(f'Invalid gid/group: {gid}')
    else:
        # Use real gid
        gid = os.getgid()

    try:
        os.setgid(gid)
    except Exception as e:
        raise Exception(f'Cannot set gid to {gid}: {e}')

    if uid is not None:
        if isinstance(uid, str):
            try:
                uid = getpwnam(uid).pw_uid
            except KeyError:
                # No user with this name - maybe its an int.
                try:
                    uid = int(uid)
                except ValueError:
                    # Nope not an int either.
                    raise Exception(f'Invalid uid/user: {uid}')
    else:
        # Use real uid
        uid = os.getuid()

    try:
        os.setuid(uid)
    except Exception as e:
        raise Exception(f'Cannot set uid to {uid}: {e}')

    # ---------------------------------------
    # Set working directory
    if working_dir:
        try:
            os.chdir(working_dir)
        except Exception as e:
            raise Exception(f'Cannot cd to {working_dir}: {e}')

    # ---------------------------------------
    # Umask
    if umask:
        if isinstance(umask, str):
            try:
                umask = int(umask, 8)
            except ValueError:
                raise Exception(f'Invalid octal umask: {umask}')

        os.umask(umask)

    # ---------------------------------------
    # Work out which file descriptors are being preserved.
    if preserve_fds is None:
        preserve_fds = _PRESERVE_FD_DEFAULT

    preserve = set()
    for fd in preserve_fds:
        # noinspection PyBroadException
        try:
            if isinstance(fd, str):
                # Treat as file name
                stat = os.stat(fd)
            elif isinstance(fd, int):
                stat = os.fstat(fd)
            else:
                raise ValueError(f'preserve_fds must be int or str not {type(fd)}')
            preserve.add((stat.st_dev, stat.st_ino))
        except ValueError:
            raise
        except Exception:  # noqa: S110
            # Ignore all other errors
            pass

    # ---------------------------------------
    # Close file descriptors - except for stdin, stdout, stderr (for now)
    # and any files specified in the preseve list.
    # We want stderr for a little bit longer.

    if close_fds:
        fd_max = max(resource.getrlimit(resource.RLIMIT_NOFILE)[0], FD_MAX)
        for fd in range(3, fd_max):
            # noinspection PyBroadException
            try:
                stat = os.fstat(fd)
                if (stat.st_dev, stat.st_ino) not in preserve:
                    os.close(fd)
            except Exception:  # noqa: S110
                pass

    # ---------------------------------------
    # Create a lockfile. Must be done after closing fds to keep lock active.

    if pidfile and not lock_file(pidfile):
        raise Exception(f'Cannot create pid file: {pidfile}')

    # ---------------------------------------
    # Setup signal handlers

    for sig_name, handler in _SIGNAL_DEFAULTS.items():
        try:
            set_signal(sig_name, handler)
        except Exception as e:
            raise Exception(f'Bad handler for signal: {sig_name}: {e}')

    if signals:
        for sig_name, handler in signals.items():
            try:
                set_signal(sig_name, handler)
            except Exception as e:
                raise Exception(f'Bad handler for signal: {sig_name}: {e}')

    # ---------------------------------------
    print(f'\n{os.getpid()}', file=sys.stderr)

    # ---------------------------------------
    # Redirect stdin, stdout, stderr to files or /dev/null

    os.closerange(0, 3)  # Be careful not to close our lockfile
    dev_null = getattr(os, 'devnull', '/dev/null')

    stdout = stdout.format(pid=os.getpid()) if stdout else dev_null
    stderr = stderr.format(pid=os.getpid()) if stderr else dev_null
    # Open fd's 0, 1 and 2 again - must be in correct order
    os.open(dev_null, os.O_RDONLY)  # stdin comes from /dev/null
    os.open(stdout, os.O_WRONLY | os.O_CREAT, 0o600)  # stdout
    os.open(stderr, os.O_WRONLY | os.O_CREAT, 0o600)  # stderr
