#!/usr/bin/env python3

"""
Test using the lava DB conn subsystem with sqlalchemy.

Just runs a COUNT(*) on the specified relation.

Usage: sqlalchemy-count [schema.]table

"""

import os
import re
import sys

from lava.connection import get_sqlalchemy_engine  # noqa: I100
from sqlalchemy import text

__author__ = 'Murray Andrews'

if len(sys.argv) != 2:
    print(f'Usage: {sys.argv[0]} [schema.]table', file=sys.stderr)
    exit(1)

relation = sys.argv[1]
if not re.match(r'^(\w+\.)?\w+$', relation):
    print(f'{sys.argv[0]}: Bad schema.table value: {relation}', file=sys.stderr)
    exit(1)

query = f'SELECT COUNT(*) FROM {relation}'

realm = None
conn_id = None

try:
    realm = os.environ['LAVA_REALM']
    conn_id = os.environ['LAVA_CONNID_DB']
except KeyError as e:
    print(f'{sys.argv[0]}: Missing environment var: {e}', file=sys.stderr)
    exit(1)

print('Connecting with sqlalchemy')
e = get_sqlalchemy_engine(conn_id, realm)
e.dialect.description_encoding = None

with e.connect() as conn:
    print(f'Running quary: {query}')
    for row in conn.execute(text(query)):
        print(row)
