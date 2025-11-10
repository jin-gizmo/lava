"""Process mgmt utilities."""

import os
from contextlib import suppress
from signal import SIGKILL
from subprocess import CalledProcessError, CompletedProcess, PIPE, Popen, TimeoutExpired, run

from .misc import Defer, Task


# ------------------------------------------------------------------------------
def killpg(pgid: int, signal: int):
    """Signal the specified process group but don't complain about non-existing groups."""

    with suppress(ProcessLookupError):
        os.killpg(pgid, signal)


# ------------------------------------------------------------------------------
# noinspection PyShadowingBuiltins
def runpg(
    *popenargs,
    start_new_session=False,
    input=None,  # noqa A002
    capture_output=False,
    timeout=None,
    check=False,
    kill_event=None,
    **kwargs,
):
    """
    Run command with arguments and return a CompletedProcess instance.

    This is almost identical to standard library `subprocess.run()` except that
    if `start_new_session` is True, instead of killing just the child process on
    termination, it kills the entire process group.

    However... This creates a second problem. Because child processes are no
    longer in the same process group as the parent, they don't get cleaned up on
    exit of the parent. If this is a problem, use the additional `kill_event` arg.

    So... If `kill_event` is set to the name of an event (e.g. "on_exit"), a
    deferred task is set recorded that can be run to kill the child process
    group by the caller at some later time. This is not an automatic process.
    The caller has to explicit request any deferred tasks be run at an
    appropriate time.

    Thanks to:
    https://alexandra-zaharia.github.io/posts/kill-subprocess-and-its-children-on-timeout-python

    Oh ... and DOS support has been removed. Suffer in your jocks DOSburgers.
    """

    if not start_new_session:
        return run(
            *popenargs,
            input=input,
            capture_output=capture_output,
            timeout=timeout,
            check=check,
            **kwargs,
        )

    # ----------------------------------------
    # From here on we are managing process groups not just a single child.

    if input is not None:
        if kwargs.get('stdin') is not None:
            raise ValueError('stdin and input arguments may not both be used.')
        kwargs['stdin'] = PIPE

    if capture_output:
        if kwargs.get('stdout') is not None or kwargs.get('stderr') is not None:
            raise ValueError('stdout and stderr arguments may not be used with capture_output.')
        kwargs['stdout'] = PIPE
        kwargs['stderr'] = PIPE

    deferred_kill_id = None
    deferred_actions = Defer.on_event(kill_event)
    with Popen(*popenargs, start_new_session=start_new_session, **kwargs) as process:
        pgid = os.getpgid(process.pid)
        if kill_event:
            deferred_kill_id = deferred_actions.add(
                Task(description=f'Kill process group {pgid}', action=killpg, args=[pgid, SIGKILL])
            )

        try:
            stdout, stderr = process.communicate(input, timeout=timeout)
        except TimeoutExpired:
            killpg(pgid, SIGKILL)
            process.wait()
            raise
        except:  # noqa E722 - Including KeyboardInterrupt, communicate handled that.
            killpg(pgid, SIGKILL)
            # We don't call process.wait() as .__exit__ does that for us.
            raise
        finally:
            if deferred_kill_id:
                deferred_actions.cancel(deferred_kill_id)
        retcode = process.poll()
        # The immediate child may have terminated but others in its process
        # group may linger, so kill the entire process group.
        killpg(pgid, SIGKILL)
        if check and retcode:
            raise CalledProcessError(retcode, process.args, output=stdout, stderr=stderr)
    return CompletedProcess(process.args, retcode, stdout, stderr)
