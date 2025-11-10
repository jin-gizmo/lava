#!/usr/bin/env python3

"""
Lava version.

This is used in a number of places (including docker builds) so don't forget to
update.

This file can be run directly to print version info to stdout.

!!! info
    As of v8.2, lava has changed from semantic versioning to PEP440 versioning.
    You would have to be doing something pretty unusual to notice the
    difference. The change was made to simplify working with PyPI. The semantic
    versioning support code has been left in, just in case, but lava itself no
    longer uses it.

"""

from __future__ import annotations

import argparse
import json
import os.path
import re
import sys
from functools import total_ordering
from pathlib import Path

from packaging.version import Version as Pep440Version

__author__ = 'Murray Andrews'


PROG = os.path.splitext(os.path.basename(sys.argv[0]))[0]


# ------------------------------------------------------------------------------
@total_ordering
class SemanticVersion:
    """
    Model semantic versions.

    :param semver: See https://semver.org
    """

    SEMVER_RE = re.compile(
        r'^(?P<major>0|[1-9]\d*)\.(?P<minor>0|[1-9]\d*)\.(?P<patch>0|[1-9]\d*)'
        r'(?:-(?P<prerelease>(?:0|[1-9]\d*|\d*[a-zA-Z-][\da-zA-Z-]*)'
        r'(?:\.(?:0|[1-9]\d*|\d*[a-zA-Z-][\da-zA-Z-]*))*))'
        r'?(?:\+(?P<buildmetadata>[\da-zA-Z-]+(?:\.[\da-zA-Z-]+)*))?$'
    )

    # --------------------------------------------------------------------------
    def __init__(self, semver: str):
        """Create."""

        m = self.SEMVER_RE.match(semver)
        if not m:
            raise ValueError(f'Bad semantic version: {semver}')

        self._version = semver
        self._components = m.groupdict()
        self.major = int(self._components['major'])
        self.minor = int(self._components['minor'])
        self.patch = int(self._components['patch'])

    # --------------------------------------------------------------------------
    def __getattr__(self, item):
        """Get a component of the semantic version."""

        return self._components[item]

    # --------------------------------------------------------------------------
    def __str__(self):
        """Generate string repreentation."""
        return self._version

    # --------------------------------------------------------------------------
    def __eq__(self, other) -> bool:
        """Compare semantic versions for equality (only care about major, minor and patch here)."""

        return all(
            (
                self.major == other.major,
                self.minor == other.minor,
                self.patch == other.patch,
            )
        )

    # --------------------------------------------------------------------------
    def __lt__(self, other) -> bool:
        """Compare semantic versions (only care about major, minor and patch here)."""

        return any(
            (
                self.major < other.major,
                self.major == other.major and self.minor < other.minor,
                self.major == other.major
                and self.minor == other.minor
                and self.patch < other.patch,
            )
        )


Version = Pep440Version

_v = json.loads((Path(__file__).parent / 'VERSION.json').read_text(encoding='utf-8'))
__VERSION__ = Version(_v['__version_num__'])
__version_num__ = str(__VERSION__)
__version_name__ = _v['__version_name__']
__version__ = f'{__version_num__} ({__version_name__})'


# ------------------------------------------------------------------------------
def process_cli_args() -> argparse.Namespace:
    """
    Process the command line arguments.

    :return:    The args namespace.
    """

    argp = argparse.ArgumentParser(
        prog=PROG,
        description='Print lava version information.',
        epilog='If no arguments are specified the lava version number is printed.',
    )

    argx = argp.add_mutually_exclusive_group()
    argx.add_argument('-n', '--name', action='store_true', help='Print version name only.')

    argx.add_argument('-a', '--all', action='store_true', help='Print all version inforamtion.')

    argx.add_argument(
        '--ge',
        action='store',
        metavar='VERSION',
        help=(
            'Exit with zero status if the lava version is greater than or equal to'
            ' the specified version.'
        ),
    )

    argx.add_argument(
        '--eq',
        action='store',
        metavar='VERSION',
        help='Exit with zero status if the lava version is equal to the specified version.',
    )

    return argp.parse_args()


# ------------------------------------------------------------------------------
def version() -> tuple[str, str]:
    """
    Get the lava version number and name.

    :return:    A tuple (version number, version name)
    """

    return __version_num__, __version_name__


# ------------------------------------------------------------------------------
def main() -> int:
    """Slip sliding along."""

    args = process_cli_args()

    if args.name:
        print(__version_name__)
        return 0
    if args.all:
        print(__version__)
        return 0
    if args.eq:
        return not bool(__VERSION__ == Version(args.eq))
    if args.ge:
        return not bool(__VERSION__ >= Version(args.ge))

    print(__version_num__)
    return 0


# ------------------------------------------------------------------------------
if __name__ == '__main__':  # pragma: no cover
    exit(main())
