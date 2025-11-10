"""SQLite3 specifics."""

from __future__ import annotations

import os
import sqlite3
from stat import S_IRUSR, S_IWUSR, S_IXUSR
from tempfile import mkdtemp, mkstemp
from typing import Any

import boto3

from lava.config import config
from lava.lib.aws import s3_download, s3_split, s3_upload
from .core import (
    LOG,
    LavaError,
    cli_connector,
    db_credentials_getter,
    expand_sql_conn_spec,
    pysql_connector,
)

__author__ = 'Murray Andrews'

CLI = """#!/bin/bash

db_file='{db_file}'

TMP=$(mktemp -d)
z=3
trap '/bin/rm -rf $TMP; exit $z' 0

if [[ "$db_file" =~ ^s3:// ]]
then
    s3_file="$db_file"
    db_file=$TMP/$(basename "$s3_file")
    aws s3 cp "$s3_file" "$db_file" || exit
    old_size=$(stat -f "%z" "$db_file")
    old_mtime=$(stat -f "%m" "$db_file")
    sleep 1
fi

sqlite3 -bail -batch "$@" "$db_file" || exit

if [ "$s3_file" != "" ]
then
    new_size=$(stat -f "%z" "$db_file")
    new_mtime=$(stat -f "%m" "$db_file")
    if [ "$old_size" -ne "$new_size" -o "$old_mtime" -ne "$new_mtime" ]
    then
        aws s3 cp "$db_file" "$s3_file"
    fi
fi

z=0
"""


# ------------------------------------------------------------------------------
# noinspection PyUnusedLocal
@db_credentials_getter('sqlite3')
def fake_creds(conn_spec: dict[str, Any], aws_session: boto3.Session = None) -> tuple[str, str]:
    """
    SQLite3 needs no creds so return random values which are then ignored.

    :param conn_spec:       A validated, expanded connection spec.
    :param aws_session:     A boto3 Session. A default is used if not specified.

    :return:                A tuple (username, password).
    """

    return 'chronosynclastic', 'infundibulum'


# ------------------------------------------------------------------------------
class Sqlite3Connection(sqlite3.Connection):
    """
    Sqlite3 connection handler that supports S3 files.

    When used with S3, the database must already exist (a zero byte file will
    do). If the file size or modification time is changed after downloading,
    them modified file is copied back to S3 when the connection is closed.

    This is a context manager. So the following works as expected:

    .. code: python

        with conn as Sqlite3Connection('file.sqlite3')
          cursor = conn.cursor()
          cursor.execute('SELECT...')

    This is mostly for testing not real production jobs but no reason it can't
    be used for that.

    :param database:    Database file. If it starts with s3:// it will be
                        staged in and out of S3 as required.

    :param aws_session: A boto3 Session(). If not specified a default is
                        created.
    :param args:        As per sqlite3 Connection().
    :param kwargs:      As per sqlite3 Connection().
    """

    # --------------------------------------------------------------------------
    def __init__(self, database: str, *args, aws_session=None, **kwargs):
        """Open an SQLite3 DB, fetching file from S3 as required."""

        self.bucket, self.key = None, None
        self._s3client = None
        self._local_db = database
        self._local_db_stat = None

        if database.startswith('s3://'):
            self.bucket, self.key = s3_split(database)

            if not aws_session:
                aws_session = boto3.Session()
            self._s3client = aws_session.client('s3')

            fd, self._local_db = mkstemp(dir=config('TMPDIR'), suffix='.sqlite3')
            os.close(fd)
            LOG.debug(f'Downloading {database} to {self._local_db}')
            try:
                s3_download(self.bucket, self.key, self._local_db, self._s3client)
            except Exception as e:
                os.unlink(self._local_db)
                raise LavaError(str(e))

            # Remember starting condition to see if we need to upload later.
            self._local_db_stat = os.stat(self._local_db)

        super().__init__(self._local_db, *args, **kwargs)

    # --------------------------------------------------------------------------
    def close(self):
        """Close the connection and push data to S3 if applicable."""

        super().close()

        if not self.bucket:
            return

        # Our file came from S3. See if it has changed.
        new_stat = os.stat(self._local_db)
        if (
            new_stat.st_size == self._local_db_stat.st_size
            and new_stat.st_mtime_ns == self._local_db_stat.st_mtime_ns
        ):
            LOG.debug(f'{self._local_db} hasn\'t changed. No need to upload to S3.')
            os.unlink(self._local_db)
            return

        LOG.debug(f'Uploading {self._local_db} to s3://{self.bucket}/{self.key}')
        try:
            s3_upload(self.bucket, self.key, self._local_db, self._s3client)
        except Exception as e:
            raise LavaError(str(e))
        finally:
            os.unlink(self._local_db)

    # --------------------------------------------------------------------------
    def __enter__(self):
        """Open context."""
        return self

    # --------------------------------------------------------------------------
    def __exit__(self, exc_type, exc_value, exc_traceback):
        """Close context."""
        self.close()


# ------------------------------------------------------------------------------
# noinspection PyUnusedLocal
@pysql_connector(dialect='sqlite3', subtype='sqlite3')
def py_connect_sqlite3(
    conn_spec: dict[str, Any],
    autocommit: bool = False,
    application_name: str = None,
) -> Sqlite3Connection:
    """
    Get a connection to the specified SQLite3 database.

    The "host" parameter is used to hold the name of the database file.
    The other connection fields are still required but are ignored (yes its a
    hack for consistency with the other database connectors.)

    :param conn_spec:       Pre-expanded connection specification
    :param autocommit:      If True, attempt to enable autocommit. This is
                            database and driver dependent as not all DBs
                            support it (e.g. sqlite3) If False, autocommit is
                            not enabled (the default state for DBAPI 2.0).
    :param application_name: Not used.

    :return:                A live DB connection. This is a context manager.

    """

    db_file = conn_spec['host']
    LOG.debug(f'sqlite3: {db_file}')

    conn = Sqlite3Connection(db_file)
    if autocommit:
        conn.isolation_level = None
    return conn


# ------------------------------------------------------------------------------
@cli_connector('sqlite3')
def cli_connect_sqlite3(
    conn_spec: dict[str, Any], workdir: str, aws_session: boto3.Session = None
) -> str:
    """
    Generate a CLI command that will run a sqlite3 script.

    Requires sqlite3 CLI to be installed and in the PATH.

    :param conn_spec:       Un-expanded connection specification.
    :param workdir:         Working directory name.
    :param aws_session:     A boto3 Session().

    :return:                Name of an executable that implements the connection.

    """

    try:
        expand_sql_conn_spec(conn_spec, aws_session=aws_session)
    except Exception as e:
        raise LavaError(f'Connection {conn_spec.get("conn_id")}: {e}')

    db_file = conn_spec['host']

    # Avoid bad chars in file name
    if any(c in db_file for c in r'\'"\\'):
        raise LavaError('Invalid database file (host parameter)')

    # ----------------------------------------
    # Create a shell script that implements the connection.

    conn_cmd_file = os.path.join(mkdtemp(dir=workdir, prefix='conn.'), 'sqlite3')
    with open(conn_cmd_file, 'w') as fp:
        print(CLI.format(db_file=db_file), file=fp)
    os.chmod(conn_cmd_file, S_IRUSR | S_IWUSR | S_IXUSR)

    return conn_cmd_file
