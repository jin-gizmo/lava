#!/usr/bin/env python3

"""Print the environment."""

import os

for k in sorted(os.environ):
    print('{}: {}'.format(k, os.environ[k]))
