#!/usr/bin/env python3

"""Test python script for lava to create temp dir and file."""

import os
import subprocess
from tempfile import mkdtemp, mkstemp

__author__ = 'Murray Andrews'

print('TMPDIR is', os.environ.get('TMPDIR'))

print('Temp file is', mkstemp())
print('Temp dir is', mkdtemp())

subprocess.run(['/bin/ls', '-laR'])
