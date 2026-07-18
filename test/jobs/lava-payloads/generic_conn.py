#!/usr/bin/env python3

"""Test generic connector in Python."""

import os
from pprint import pprint

from lava.connection import get_generic_connection

__author__ = 'Murray Andrews'

conn_id = os.environ['LAVA_CONNID_GENERIC']
realm = os.environ['LAVA_REALM']

conn = get_generic_connection(conn_id, realm)
pprint(conn)
