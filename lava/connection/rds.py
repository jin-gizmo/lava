"""
AWS RDS specifics.

Mostly these just use the other DB connectors (postgres, mysql etc.)

"""

from __future__ import annotations

from typing import Any

import boto3

from lava.connection.core import db_credentials_getter

__author__ = 'Murray Andrews'


# ------------------------------------------------------------------------------
@db_credentials_getter('postgres-aurora', 'postgres-rds', 'mysql-aurora', 'mysql-rds')
def get_rds_creds_with_iam(
    conn_spec: dict[str, Any], aws_session: boto3.Session = None
) -> tuple[str, str]:
    """
    Get an AWS RDS username, password using generate_db_auth_token.

    :param conn_spec:       A validated, expanded connection spec.
    :param aws_session:     A boto3 Session. A default is used if not specified.

    :return:                A tuple (username, password).
    """

    if not aws_session:
        aws_session = boto3.Session()

    token = aws_session.client('rds').generate_db_auth_token(
        DBHostname=conn_spec['host'],
        Port=conn_spec['port'],
        DBUsername=conn_spec['user'],
    )

    return conn_spec['user'], token
