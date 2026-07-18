#!/usr/bin/env python3

"""Test the aws connector in Python."""

import os
from pprint import pprint

from lava.connection import get_aws_session

realm = os.environ['LAVA_REALM']
conn_id = os.environ['LAVA_CONNID_AWS']


aws_session = get_aws_session(conn_id, realm)

sts = aws_session.client('sts')
print(80 * '~')
pprint(sts.get_caller_identity())
print(80 * '~')
