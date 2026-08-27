#!/usr/bin/env python3
"""
Simple exorciser for DB connections.

This just does a `SELECT 1` on every connection it finds in LAVA_CONN* env vars.
"""

import json
import os
import sys
from pathlib import Path
from subprocess import run
from typing import Any

import boto3

from lava.connection import get_pysql_connection

PROG = Path(sys.argv[0]).stem


# ------------------------------------------------------------------------------
def do_python_connections() -> dict[str, Any]:
    """Exercise the Python based connections."""

    aws_session = boto3.Session()
    db_conn_ids = {k: v for k, v in os.environ.items() if k.startswith('LAVA_CONNID_')}
    if not db_conn_ids:
        raise RuntimeError('No LAVA_CONNID_* environment variables found')

    realm = os.environ['LAVA_REALM']
    results = {}
    for var, conn_id in db_conn_ids.items():
        conn = None
        try:
            conn = get_pysql_connection(conn_id, realm, aws_session=aws_session)
            cursor = conn.cursor()
            cursor.execute('SELECT 1')
            r = cursor.fetchone()
            # Not all query results are JSON serialisable. e.g. the mssql
            # driver returns "Row" objects.
            results[var] = {'conn_id': conn_id, 'result': [v for v in r]}
        except Exception as e:
            raise RuntimeError(f'{var}: {conn_id}: {e}')
        finally:
            if conn:
                conn.close()  # noqa

    return results


# ------------------------------------------------------------------------------
def do_cli_connections() -> dict[str, Any]:
    """Exercise the CLI based connections."""

    db_conn_scripts = {k: v for k, v in os.environ.items() if k.startswith('LAVA_CONN_')}
    if not db_conn_scripts:
        raise RuntimeError('No LAVA_CONN_* environment variables found')

    results = {}
    for var, script_file in db_conn_scripts.items():

        try:
            # Semi-colon on query is important for Oracle
            r = run([script_file], text=True, capture_output=True, check=True, input='SELECT 1;')
        except Exception as e:
            raise RuntimeError(f'{var}: {e}')

        results[var] = {
            'script_file': script_file,
            # 'script': Path(script_file).read_text(),
            'stdout': r.stdout,
            'stderr': r.stderr,
        }

    return results


# ------------------------------------------------------------------------------
def main() -> int:
    """Show time."""

    results = do_python_connections() | do_cli_connections()
    json.dump(results, sys.stdout, indent=4)
    print()

    return 0


# ------------------------------------------------------------------------------
if __name__ == '__main__':
    try:
        exit(main())
    except Exception as ex:
        print(f'{PROG}: {ex}', file=sys.stderr)
        sys.exit(1)
