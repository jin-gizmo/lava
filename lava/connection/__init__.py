"""Lava connection subssystem API."""

# ruff: noqa: F401

import lava.connection.mssql
import lava.connection.mysql
import lava.connection.oracle
import lava.connection.postgres
import lava.connection.rds
import lava.connection.redshift
import lava.connection.smb
import lava.connection.sqlite3
from .aws import get_aws_connection, get_aws_session
from .core import (
    get_cli_connection,
    get_connection_spec,
    get_pysql_connection,
    get_smb_connection,
)
from .docker import get_docker_connection
from .email import get_email_connection
from .generic import cli_connect_generic, get_generic_connection
from .sharepoint import get_sharepoint_connection
from .slack import get_slack_connection
from .sqlalchemy import get_sqlalchemy_engine
from .ssh import install_ssh_key

__author__ = 'Murray Andrews'

__all__ = [
    'cli_connect_generic',
    'get_aws_connection',
    'get_aws_session',
    'get_cli_connection',
    'get_connection_spec',
    'get_docker_connection',
    'get_email_connection',
    'get_generic_connection',
    'get_pysql_connection',
    'get_sharepoint_connection',
    'get_slack_connection',
    'get_smb_connection',
    'get_sqlalchemy_engine',
    'install_ssh_key',
]
