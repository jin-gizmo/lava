"""File operation utilities."""

from __future__ import annotations

import errno
import fcntl
import math
import os
import re
import shlex
import subprocess
import unicodedata
from collections.abc import Iterator
from fnmatch import fnmatch

from .decorators import deprecated

__author__ = 'Murray Andrews'


# ------------------------------------------------------------------------------
@deprecated('Just use os.makedirs() instead')
def makedir(d: str) -> None:
    """
    Create the specified directory (and parents) if it doesn't exist.

    !!! warning "Deprecated as of v8.1.0"
        Just use os.makedirs() instead.

    It is an error for d to already exist if its not a directory. Note that
    Python 2.7 makedirs() has no exist_ok support.

    :param d:           Directory name.

    :raise Exception:   If d cannot be created or it already exists and is not
                        a directory.
    """

    if os.path.exists(d):
        if os.path.isdir(d):
            return
        raise Exception(f'{d} exists but is not a directory')

    os.makedirs(d)


# ------------------------------------------------------------------------------
def delete_files(*args: str) -> None:
    """
    Delete the files whose names are specified as arguments.

    :param args:         File name(s). Empty values are ignored.

    :raise Exception:   If any of the files could not be deleted. Attempting to
                        delete a non-existent file is not an error.

    """

    failures = []

    for f in args:
        if not f:
            continue
        try:
            os.remove(f)
        except OSError as e:
            # Trying to delete non-existent file is not considered an error
            if e.errno != errno.ENOENT:
                failures.append(f)

    if failures:
        raise Exception(f'Could not delete file(s): {", ".join(failures)}')


# ------------------------------------------------------------------------------
def fsplit(
    filename: str, prefix: str, maxsize: int, suffixlen: int = 0, delete: bool = False
) -> Iterator[str]:
    """
    Rough split a text file into pieces approximately maxsize or below.

    Pieces are allowed to be slightly larger than maxsize. Returns an iterator
    of file names. It's the caller's problem to make sure the chunks don't
    overwrite anything important.

    :param filename:    Name of the file to split. Must be a text file.
    :param prefix:      A prefix that will be used to generate the names of the
                        split files.
    :param maxsize:     Maximum size of each split file.
    :param suffixlen:   The number of digits to use in the suffix for the split
                        files. An attempt is made to estimate the number of
                        digits required and the larger of the supplied value
                        and the estimated value is used. Note that this can still
                        fail to allocate enough digits in certain circumstances.
                        An exception occurs when this happens.
    :param delete:      If True, delete the original file after splitting.
                        Default False.

    :return:            An iterator returning file names of the split files.

    """

    # How many digits do we need. Use the larger of the provided value and an
    # estimate based on file size. Note that this can fail to allocate enough
    # digits on occasion.

    filesize = os.path.getsize(filename)
    suffixlen = math.ceil(max(float(suffixlen), math.log10(1.0 * filesize / maxsize)))

    splitnum = 0
    linenum = 0
    splitsize = 0
    splitfile = None
    ofp = None

    with open(filename) as ifp:
        for line in ifp:
            linenum += 1

            if len(line) + splitsize > maxsize and ofp:
                # Need to start a new file?
                ofp.close()
                ofp = None
                yield splitfile

            if len(line) > maxsize:
                raise Exception(f'Cannot split {filename} - line {linenum} is too long')

            if not ofp:
                # Start a new split file
                splitnum += 1

                if splitnum > 10**suffixlen:
                    raise Exception(
                        f'Cannot split {filename} - overflowed suffixlen of {suffixlen}'
                    )

                splitsize = 0
                splitfile = prefix + f'{splitnum:0{suffixlen}d}'
                if splitfile == filename:
                    raise Exception('fsplit chunk will overwrite original')

                ofp = open(splitfile, 'w')  # noqa: SIM115

            ofp.write(line)
            splitsize += len(line)

    # Final fragment
    if ofp:
        ofp.close()
        yield splitfile

    if delete:
        delete_files(filename)


# ------------------------------------------------------------------------------
_lock_fp = None


def lock_file(fname: str) -> bool:
    """
    Create a lock file with the given name and write the current process PID.

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

    # noinspection PyTypeChecker
    print(os.getpid(), file=_lock_fp)
    _lock_fp.flush()
    return True


# ------------------------------------------------------------------------------
# Map glob to an unpacker
UNPACKERS = [
    ('*.zip', 'unzip -o -qq -d {dirname} {pkg}'),
    ('*.tar', 'tar -x -C {dirname} -f {pkg}'),
    ('*.tar.*', 'tar -x -C {dirname} -f {pkg}'),
]


def unpack(pkg: str, dirname: str, timeout: int = 30) -> None:
    """
    Extract the specified package (e.g. tar or zip) into the specified directory.

    Existing files will be overwritten.

    :param pkg:         The filename of the package.
    :param dirname:     The target directory. This will be created if it doesn't
                        exist.
    :param timeout:     Time limit on extraction in seconds. Default 30 seconds.

    """

    base = os.path.basename(pkg)

    for pat, unpacker in UNPACKERS:
        if fnmatch(base, pat):
            # Found an unpacker
            try:
                subprocess.check_output(
                    shlex.split(unpacker.format(dirname=dirname, pkg=pkg)),
                    stdin=subprocess.DEVNULL,
                    stderr=subprocess.STDOUT,
                    timeout=timeout,
                )
            except subprocess.CalledProcessError as e:
                raise Exception(f'Cannot unpack {pkg} to {dirname}: {e.output}')

            return

    raise Exception(f'Don\'t know how to unpack {pkg}')


# ------------------------------------------------------------------------------
def read_head_or_tail(filename: str, size: int) -> str:
    """
    Read a limited size chunk from the beginning (or end) of a file.

    :param filename:    Name of file.
    :param size:        Maximum number of bytes to read. Less data may be read
                        if the file is smaller. If positive, read from the start
                        of the file. If negative, read abs(size) bytes from the
                        end of the file.
    :return:            The data as a string.
    """

    if not size:
        return ''

    with open(filename) as fp:
        if size < 0:
            # Need to make sure we don't try to seek before start of file
            os.lseek(fp.fileno(), max(size, -os.path.getsize(filename)), os.SEEK_END)
        return fp.read(abs(size))


# ------------------------------------------------------------------------------
def sanitise_filename(value: str) -> str:
    """
    Turn an arbitrary string into something safe as a local filename.

    This code is based on slugify() from Django.

    :param value:       String to sanitise.
    :return:            Sanitised string

    """

    value = str(value)
    value = unicodedata.normalize('NFKD', value).encode('ascii', 'ignore').decode('ascii')
    value = re.sub(r'[^./=+\w\s-]', '', value).strip().lower()
    value = re.sub(r'[/.]+', '.', value)
    value = re.sub(r'[-\s]+', '-', value)

    return value.strip('.-')
