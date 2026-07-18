#!/usr/bin/env python3

"""Test python script for lava."""

import os

__author__ = 'Murray Andrews'

from lava.version import __version__

print('VERSION is', __version__)
print('PYTHONPATH is', os.environ.get('PYTHONPATH'))
