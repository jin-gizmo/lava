"""
Database utilities.

!!! danger
    This is **not** a general purpose database interface layer. Do not attempt
    to use it for that. It is designed specifically to support lava jobs which
    have very specific needs and is subject to change.

"""

from __future__ import annotations

import csv
import gzip
import logging
import os.path
import re
import signal
import subprocess
from collections.abc import Callable, Iterator
from os import unlink
from tempfile import mkdtemp, mkstemp
from time import sleep
from typing import Any

import boto3
from pg8000 import ProgrammingError

from lava.config import config
from lava.connection import get_cli_connection, get_pysql_connection
from lava.lib.aws import s3_load_json, s3_set_object_encoding, s3_split
from lava.lib.datetime import duration_to_seconds
from lava.lib.decorators import deprecated
from lava.lib.misc import dict_select, is_quoted

__author__ = 'Murray Andrews'

_DB_HANDLERS = {}


# ------------------------------------------------------------------------------
def db_handler(*args: str) -> Callable:
    """
    Register database handler classes.

    Usage:

        @db_handler(db_type1, ...)
        a_class(...)

    :param args:        A list of database types that the decorated class
                        handles.

    """

    def decorate(cls):
        """
        Register the handler cls.

        :param cls:     Class to register.
        :return:        Unmodified class.

        """
        for db_type in args:
            if db_type in _DB_HANDLERS:
                raise Exception(f'{db_type}  is already registered')
            _DB_HANDLERS[db_type] = cls
        return cls

    return decorate


# ------------------------------------------------------------------------------
def read_manifest(
    bucket: str, key: str, aws_session: boto3.Session = None
) -> list[tuple[str, str]]:
    """
    Read a manifest file from S3 and return the list of files.

    :param bucket:      Bucket name
    :param key:         S3 key.
    :param aws_session: A boto3 Session.

    :return:            A list of S3 object names in the form (bucket, key)
    """

    manifest_data = s3_load_json(bucket, key, aws_session)
    return [s3_split(x['url']) for x in manifest_data['entries']]


# ------------------------------------------------------------------------------
class Database:
    """
    Base class for a database handler.

    This is not a generic database model but rather a specific adaptation for
    the purposes of lava.

    :param conn_spec:   A database connection specification.
    :param realm:       Lava realm.
    :param tmpdir:      Temporary directory for junk if required. It is
                        assumed that the directory already exists and that
                        caller will clean this up.
    :param aws_session: A boto3 Session(). If not specified a default will
                        be created. Default None.
    :param logger:      A logger. If not specified, use the root logger.
    :param application_name: Application name when connecting.

    """

    # --------------------------------------------------------------------------
    def __init__(
        self,
        conn_spec: dict[str, Any],
        realm: str,
        tmpdir: str,
        aws_session: boto3.Session = None,
        logger: logging.Logger = None,
        application_name: str = None,
    ):
        """Create a new Database instance."""

        self.conn_spec = conn_spec
        self.realm = realm
        self.aws_session = aws_session if aws_session else boto3.Session()
        self.logger = logger if logger else logging.getLogger()
        self.application_name = application_name

        # ANSI left and right quotes. Must be one or 2 char string. Subclasses
        # can override or just implement their own object_name() method.
        self.quotes = '"'

        # Don't fold case of database object names when quoting them.
        self.preserve_case = conn_spec.get('preserve_case', False)

        # Yes, I know this looks strange, but the tmpdir provided by lava at
        # this point could be shared by multiple simultaneous jobs running at
        # the same time (due to the dag job type's children running under the
        # same run ID in parallel). So we need to guard against clashes by
        # adding another layer of ... err... tempness.
        self.tmpdir = mkdtemp(dir=tmpdir, prefix='db.')

        self._conn = None
        self._cursor = None
        self._columns = {}

    # --------------------------------------------------------------------------
    @staticmethod
    def handler(db_type: str, *args, **kwargs) -> Database:
        """
        Create a database handler for the specified DB type.

        :param db_type:     A name for the database type. eg. 'redshift'.

        :return:            A database handler.
        """

        return _DB_HANDLERS[db_type](*args, **kwargs)

    # --------------------------------------------------------------------------
    @property
    def conn(self):
        """
        Get a database connection.

        An existing connection will be reused if available.

        Default implementation returns a DBAPI 2.0 connection object.

        :return:        A database connection.
        """

        if not self._conn:
            self._conn = get_pysql_connection(
                conn_id=self.conn_spec['conn_id'],
                realm=self.realm,
                aws_session=self.aws_session,
                application_name=self.application_name,
            )
        return self._conn

    # --------------------------------------------------------------------------
    @property
    def cursor(self):
        """
        Return a cursor.

        A cached cursor will be used if available.

        :return:        A DBAPI 2.0 cursor.
        """

        if not self._cursor:
            self._cursor = self.conn.cursor()

        return self._cursor

    # --------------------------------------------------------------------------
    def close(self) -> None:
        """Close any open connections."""

        if self._conn:
            self._conn.close()
            self._cursor = None
            self._conn = None

    # --------------------------------------------------------------------------
    # noinspection PyMethodMayBeStatic
    def object_name(self, *name_part: str) -> str:
        """
        Sanitise a database object name.

        This may involve rejecting or quoting unsafe object names. The default
        implementation just uses ANSI style quoting with double quotes.

        By default, object names are converted to lower case. This presents a
        problem with respect to case sensitivity in some cases. To mitigate this,
        the `preserve_case` field in the connection specification can be set to
        prevent case folding.

        The method is not static to preserve the option for implementations to
        adjust behaviour based on the conn spec.

        :param name_part:   One or more name parts. Empty parts are silently
                            discarded.
        :return:            A clean object name composed of the parts.
        """

        for s in name_part:
            if any(q in s for q in self.quotes):
                raise ValueError(f'Bad database object name: {s}')

        return '.'.join(
            f'{self.quotes[0]}{s if self.preserve_case else s.lower()}{self.quotes[-1]}'
            for s in name_part
            if s
        )

    # --------------------------------------------------------------------------
    def truncate_table(self, schema: str, table: str) -> None:
        """
        Truncate the specified table.

        DBs tend to vary in terms of handling of transactions around truncates.

        :param schema:      Schema name
        :param table:       Table name

        """

        sql = f'TRUNCATE TABLE {self.object_name(schema, table)}'
        self.logger.debug('SQL: %s', sql)
        self.cursor.execute(sql)

    # --------------------------------------------------------------------------
    def create_table(self, schema: str, table: str, columns: list[str]) -> None:
        """
        Create a table.

        !!! warning
            There is s still a (low) risk SQL injection here in the column specs,
            however these are not injected at runtime in lava and are part of the
            job spec.

        :param schema:      Schema name.
        :param table:       Table name.
        :param columns:     A list of column specifications.

        """

        sql = f'CREATE TABLE {self.object_name(schema, table)} ({", ".join(columns)})'
        self.logger.debug('SQL: %s', sql)
        self.cursor.execute(sql)

    # --------------------------------------------------------------------------
    def drop_table(self, schema: str, table: str) -> None:
        """
        Drop a table.

        :param schema:      Schema name.
        :param table:       Table name.

        """

        sql = f'DROP TABLE IF EXISTS {self.object_name(schema, table)}'
        self.logger.debug('SQL: %s', sql)
        self.cursor.execute(sql)

    # --------------------------------------------------------------------------
    def table_is_empty(self, schema: str, table: str) -> bool:
        """
        Check if a given table is empty.

        For some DBs (e.g. Postgres), a simple row count is a really bad idea on
        big tables (unlike Redshift).

        :param schema:      Schema name.
        :param table:       Table name.

        :return:            True if the table is empty. False otherwise.

        """

        sql = f'SELECT 1 FROM {self.object_name(schema, table)} LIMIT 1'  # noqa: S608
        self.logger.debug('SQL: %s', sql)
        self.cursor.execute(sql)
        return not self.cursor.fetchone()

    # --------------------------------------------------------------------------
    def table_exists(self, schema: str, table: str) -> bool:
        """
        Check if a table (or view) exists.

        Visibility of table existence is dependent on the database access
        permissions of the user owning the connection.

        Works on any DB that supports the information_schema.

        We can't easily use query parameters without handling all the possible
        DBAPI 2.0 paramstyle settings. To reduce risk of injection, object
        names containing single quotes are rejected.

        :param schema:      Schema name.
        :param table:       Table name.

        :return:            True if the table exists.

        """

        if "'" in schema:
            raise ValueError(f'Bad schema name: {schema}')

        if "'" in table:
            raise ValueError(f'Bad table name: {table}')

        sql = f"""
                SELECT 1 FROM information_schema.tables
                WHERE table_schema = '{schema}'
                  AND table_name = '{table}'
            """  # noqa: S608
        self.cursor.execute(sql)
        self.logger.debug('SQL: %s', sql)
        return bool(self.cursor.fetchone())

    # --------------------------------------------------------------------------
    def columns(self, schema: str, table: str) -> list[str]:
        """
        Get the column names for the given table.

        Works on any DB that supports the information_schema. Results are
        cached.

        We can't easily use query parameters without handling all the possible
        DBAPI 2.0 paramstyle settings. To reduce risk of injection, object
        names containing single quotes are rejected.

        :param schema:      Schema name.
        :param table:       Table name.

        :return:            A list of column names.

        """

        if "'" in schema:
            raise ValueError(f'Bad schema name: {schema}')

        if "'" in table:
            raise ValueError(f'Bad table name: {table}')

        t = f'{schema}.{table}'

        if t not in self._columns:
            self.cursor.execute(
                f"""
                SELECT column_name
                FROM information_schema.columns
                WHERE table_schema = '{schema}'
                  AND table_name = '{table}'
                """  # noqa: S608
            )
            self._columns[t] = [row[0].lower() for row in self.cursor.fetchall()]

        return self._columns[t]

    # --------------------------------------------------------------------------
    def copy_from_s3(
        self,
        schema: str,
        table: str,
        bucket: str,
        key: str,
        region: str = None,
        copy_args: list[str] = None,
        load_columns: list[str] = None,
        s3_access_keys: dict[str, str] = None,
        iam_role: str = None,
        min_size: int = 0,
    ) -> list[str]:
        """
        Copy a file from S3 to a specific database table.

        No commit is done.

        :param schema:          Target schema name.
        :param table:           Target table names.
        :param copy_args:       Copy arguments.
        :param bucket:          Source bucket name.
        :param key:             Source key in S3.
        :param region:          AWS region containing the bucket.
        :param load_columns:    A list of columns to load. May be empty which
                                means load all.
        :param s3_access_keys:  Access keys to access S3. Must be a dictionary
                                with aws_access_key_id and aws_secret_access_key.
        :param iam_role:        IAM role name to access S3. Some DBs use it, some
                                don't.
        :param min_size:        Try to avoid loading data files below this size
                                in bytes. Some subclasses may honour this.
                                Some not.

        :return:                A list of strings indicating steps taken.

        """

        raise NotImplementedError('copy_from_s3')


# ------------------------------------------------------------------------------
@db_handler('postgres-aurora', 'postgres-rds')
class PostgresRds(Database):
    """Model a Postgres RDS / Aurora database."""

    COPY_PARAMS = {
        'FORMAT',
        'HEADER',
        'OIDS',
        'FREEZE',
        'DELIMITER',
        'NULL',
        'QUOTE',
        'ESCAPE',
        'FORCE_NOT_NULL',
        'FORCE_NULL',
        'ENCODING',
        # Non-standard args
        'MANIFEST',
        'GZIP',
    }

    # --------------------------------------------------------------------------
    def copy_from_s3(
        self,
        schema: str,
        table: str,
        bucket: str,
        key: str,
        region: str = None,
        copy_args: list[str] = None,
        load_columns: list[str] = None,
        s3_access_keys: dict[str, str] = None,
        iam_role: str = None,
        min_size: int = 0,
    ) -> list[str]:
        """
        Copy a file from S3 to Postgres RDS / Aurora with S3 native COPY.

        There is also a degree of trickery here to support handling of
        manifests.

        :param schema:          Target schema name.
        :param table:           Target table names.
        :param copy_args:       Copy arguments. In addition to the standard
                                Postrges COPY args the following are also
                                supported: MANIFEST, GZIP.
        :param bucket:          Source bucket name.
        :param key:             Source key in S3.
        :param region:          AWS region containing the bucket.
        :param load_columns:    A list of columns to load. May be empty which
                                means load all.
        :param s3_access_keys:  Access keys to access S3.
        :param iam_role:        Not used.
        :param min_size:        Try to avoid loading data files below this size
                                in bytes.

        :return:                A list of strings indicating steps taken.

        """

        # ----------------------------------------
        # Validate COPY parameters.

        copy_args_dict = {p.split()[0].upper(): p for p in copy_args} if copy_args else {}
        bad_args = set(copy_args_dict) - self.COPY_PARAMS
        if bad_args:
            raise ValueError(f'Invalid COPY arguments: {", ".join(bad_args)}')

        # ----------------------------------------

        events = []

        # This s3 client is used to set metadata on the source object if needed.
        # It is not used for the copy process.
        s3_client = self.aws_session.client('s3')

        # These S3 access keys are used in the copy process. If not specified we
        # have to assume there is an IAM role on the DB that will work.
        if not s3_access_keys:
            s3_access_keys = {
                'aws_access_key_id': '',
                'aws_secret_access_key': '',
                'aws_session_token': '',
            }
        else:
            s3_access_keys = {'aws_session_token': ''} | s3_access_keys

        # ----------------------------------------
        # Prepare some of the copy params

        target = self.object_name(schema, table)
        col_list = (
            ','.join([self.object_name(c.split(' ', 1)[0]) for c in load_columns])
            if load_columns
            else ''
        )

        # Fake manifest handling
        if 'MANIFEST' in copy_args_dict:
            del copy_args_dict['MANIFEST']
            self.logger.debug(f'Reading manifest s3://{bucket}/{key}')
            events.append(f'Reading manifest s3://{bucket}/{key}')
            key_list = read_manifest(bucket, key)
        else:
            key_list = [(bucket, key)]

        if 'GZIP' in copy_args_dict:
            del copy_args_dict['GZIP']
            self.logger.debug('Setting ContentEncoding to gzip')
            for b, k in key_list:
                try:
                    s3_set_object_encoding(b, k, 'gzip', s3_client)
                except Exception as e:
                    raise Exception(f's3://{b}/{k}: {e}')

            # Wait for S3 to settle down. Very important.
            sleep(5)

        # Allow a non-standard * argument on the following options as a
        # shorthand for all columns.
        for k in 'FORCE_NULL', 'FORCE_NOT_NULL':
            if k in copy_args_dict:
                a = re.split(r'\s+', copy_args_dict[k], maxsplit=1)
                if len(a) == 2 and a[1].strip() == '*':
                    copy_args_dict[k] = '{} ({})'.format(
                        k, ', '.join(self.object_name(c) for c in self.columns(schema, table))
                    )

        copy_args_s = ', '.join(copy_args_dict.values()).replace("'", "''") if copy_args else ''

        # ----------------------------------------
        # Load our list of objects.

        events.append(f'Running COPY command(s) for {schema}.{table}')

        safe_copy_cmd = f"""
                SELECT aws_s3.table_import_from_s3(
                    '{target}',
                    '{col_list}',
                    '({copy_args_s})',
                    '{{bucket}}',
                    '{{key}}',
                    '{region}',
                    '{{aws_access_key_id}}',
                    '{{aws_secret_access_key}}',
                    '{{aws_session_token}}'
                )
                """

        self.logger.debug(f'COPY command: {safe_copy_cmd}')
        events.append(f'COPY command: {safe_copy_cmd}')

        for b, k in key_list:
            # ------------------------------------
            # Skip runts

            self.logger.debug(f'Loading s3://{bucket}/{key}')

            if min_size:
                # Wasteful for gzips have - already done head object. Fix one day.
                try:
                    file_info = s3_client.head_object(Bucket=b, Key=k)
                except Exception as e:
                    raise Exception(f's3://{b}/{k}: {e}')

                if file_info['ContentLength'] < min_size:
                    events.append(f'Skipping runt file s3://{b}/{k}')
                    continue

            events.append(f'Copying s3://{b}/{k}')
            copy_cmd = safe_copy_cmd.format(bucket=b, key=k, **s3_access_keys)

            # ----------------------------------------
            try:
                self.cursor.execute(copy_cmd)
            except ProgrammingError as e:
                # Postgres copy unhelpfully reports error where there was none
                if ' 0 rows were copied successfully' not in e.args[0].get('M', ''):
                    raise
                result = 'File was empty'
            else:
                result = self.cursor.fetchone()[0]

            events.append('Copy complete')
            events.append(result)

        return events


# ------------------------------------------------------------------------------
@db_handler('mysql-aurora')
class AuroraMySql(Database):
    """Model an Aurora MySQL database."""

    COPY_PARAMS = {
        'REPLACE',
        'IGNORE',
        'PARTITION',
        'FILE',
        'PREFIX',
        'MANIFEST',
        # Non-standard args
        'DELIMITER',
        'ENCODING',
        'QUOTE',
        'ESCAPE',
        'HEADER',
        'TERMINATOR',
    }

    ANSI_QUOTES = False

    # --------------------------------------------------------------------------
    def __init__(self, *args, **kwargs):
        """Init."""

        super().__init__(*args, **kwargs)

        self.quotes = '"' if self.ANSI_QUOTES else '`'

    # --------------------------------------------------------------------------
    def copy_from_s3(
        self,
        schema: str,
        table: str,
        bucket: str,
        key: str,
        region: str = None,
        copy_args: list[str] = None,
        load_columns: list[str] = None,
        s3_access_keys: dict[str, str] = None,
        iam_role: str = None,
        min_size: int = 0,
    ) -> list[str]:
        """
        Copy a file from S3 to Aurora MySQL with S3 native COPY.

        At the lava user level we have departed significantly from the native
        Aurora COPY command to try to give some alignment with Postgres.

        :param schema:          Target schema name.
        :param table:           Target table names.
        :param copy_args:       Copy arguments. In addition to the standard
                                Postrges COPY args the following are also
                                supported: MANIFEST, GZIP.
        :param bucket:          Source bucket name.
        :param key:             Source key in S3.
        :param region:          AWS region containing the bucket.
        :param load_columns:    A list of columns to load. May be empty which
                                means load all.
        :param s3_access_keys:  Not used.
        :param iam_role:        Not used.
        :param min_size:        Try to avoid loading data files below this size
                                in bytes.

        :return:                A list of strings indicating steps taken.

        """

        # ----------------------------------------
        # Validate COPY parameters.

        copy_args_dict = {p.split()[0].upper(): p for p in copy_args} if copy_args else {}
        bad_args = set(copy_args_dict) - self.COPY_PARAMS
        if bad_args:
            raise ValueError(f'Invalid COPY arguments: {", ".join(bad_args)}')

        # ----------------------------------------

        events = []

        if min_size:
            s3_client = self.aws_session.client('s3')
            try:
                file_info = s3_client.head_object(Bucket=bucket, Key=key)
            except Exception as e:
                raise Exception(f's3://{bucket}/{key}: {e}')

            if file_info['ContentLength'] < min_size:
                events.append(f'Skipping runt file s3://{bucket}/{key}')
                return events

        # Prepare some of the copy params

        target = self.object_name(schema, table)
        col_list = (
            '({})'.format(','.join([self.object_name(c.split(' ', 1)[0]) for c in load_columns]))
            if load_columns
            else ''
        )

        # . . . . . . . . . . . . . . . . . . . .
        # Load type

        x = dict_select(copy_args_dict, 'FILE', 'PREFIX', 'MANIFEST')
        if len(x) > 1:
            raise ValueError('Only one of FILE | PREFIX | MANIFEST allowed')
        load_type = next(iter(x)) if x else 'FILE'

        # . . . . . . . . . . . . . . . . . . . .
        # s3 URI

        s3_uri = f's3-{region}://{bucket}/{key}' if region else f's3://{bucket}/{region}'

        # . . . . . . . . . . . . . . . . . . . .
        # REPLACE / IGNORE

        x = dict_select(copy_args_dict, 'IGNORE', 'REPLACE')
        if len(x) > 1:
            raise ValueError('Only one of IGNORE | REPLACE allowed')
        replace_ignore = next(iter(x)) if x else ''

        # . . . . . . . . . . . . . . . . . . . .
        # PARTITION

        partition = copy_args_dict.get('PARTITION', '')

        # . . . . . . . . . . . . . . . . . . . .
        # CHARACTER SET / ENCODING

        if 'ENCODING' in copy_args_dict:
            x = copy_args_dict['ENCODING'].split()
            if len(x) == 2:
                charset = f'CHARACTER SET {x[1]}'
            else:
                raise ValueError('Usage: ENCODING charset-name')
        else:
            charset = ''

        # . . . . . . . . . . . . . . . . . . . .
        # Field termination and quoting

        column_format = []

        if 'DELIMITER' in copy_args_dict:
            x = copy_args_dict['DELIMITER'].split()
            if len(x) == 2 and is_quoted(x[1]):
                column_format.append(f'TERMINATED BY {x[1]}')
            else:
                raise ValueError("Usage: DELIMITER 'string'")

        if 'QUOTE' in copy_args_dict:
            x = copy_args_dict['QUOTE'].split()
            if len(x) == 3 and x[1].upper() == 'OPTIONAL' and is_quoted(x[2]):
                column_format.append(f'OPTIONALLY ENCLOSED BY {x[2]}')
            elif len(x) == 2 and is_quoted(x[1]):
                column_format.append(f'ENCLOSED BY {x[1]}')
            else:
                raise ValueError("Usage: QUOTE [OPTIONAL] 'char'")

        if 'ESCAPE' in copy_args_dict:
            x = copy_args_dict['ESCAPE'].split()
            if len(x) == 2 and is_quoted(x[1]):
                column_format.append(f'ESCAPED BY {x[1]}')
            else:
                raise ValueError("Usage: ESCAPE 'char'")

        column_format = 'COLUMNS ' + ' '.join(column_format) if column_format else ''

        # Are we there yet?

        # . . . . . . . . . . . . . . . . . . . .
        # Line terminator. We don't handle the ROWS option in the base copy.

        if 'TERMINATOR' in copy_args_dict:
            x = copy_args_dict['TERMINATOR'].split()
            if len(x) == 2 and is_quoted(x[1]):
                terminator = f'LINES TERMINATED BY {x[1]}'
            elif len(x) == 2 and x[1].upper() == 'UNIX':
                terminator = r"LINES TERMINATED BY '\n'"
            elif len(x) == 2 and x[1].upper() == 'DOS':
                terminator = r"LINES TERMINATED BY '\r\n'"
            else:
                raise ValueError("Usage: TERMINATOR UNIX|DOS|'string'")
        else:
            terminator = ''

        # . . . . . . . . . . . . . . . . . . . .
        # Skip header

        if 'HEADER' in copy_args_dict:
            x = copy_args_dict['HEADER'].split()
            if len(x) == 1:
                # Default to 1 header line
                skip_header = 'IGNORE 1 LINES'
            elif len(x) == 2:
                skip_header = f'IGNORE {x[1]} LINES'
            else:
                raise ValueError('Usage: HEADER [number]')
        else:
            skip_header = ''

        # ----------------------------------------
        # Run the COPY

        copy_cmd = f"""
                LOAD DATA FROM S3 {load_type} '{s3_uri}'
                {replace_ignore}
                INTO TABLE {target}
                {partition}
                {charset}
                {column_format}
                {terminator}
                {skip_header}
                {col_list}
                """

        # Squish whitespace
        copy_cmd = re.sub(r'\s+', ' ', copy_cmd).strip()
        self.logger.debug(f'COPY command: {copy_cmd}')
        events.append(copy_cmd)

        # ----------------------------------------
        events.append(f'Running COPY command for {schema}.{table}')
        try:
            rec_count = self.cursor.execute(copy_cmd)
        except Exception as e:
            self.logger.debug(f'Exception from copy command: {e}')
            raise
        else:
            result = self.cursor.fetchone()

        events.append(f'Copy to {schema}.{table} complete')
        events.append(f'{rec_count} records processed')
        if result:
            events.append(result)

        return events


# ------------------------------------------------------------------------------
@db_handler('postgres', 'psql')
class Postgres(Database):
    """Model a conventional Postgres database."""

    COPY_PARAMS = {
        'FORMAT',
        'HEADER',
        'OIDS',
        'FREEZE',
        'DELIMITER',
        'NULL',
        'QUOTE',
        'ESCAPE',
        'FORCE_NOT_NULL',
        'FORCE_NULL',
        'ENCODING',
        # Non-standard args
        'MANIFEST',
        'GZIP',
    }

    # --------------------------------------------------------------------------
    def __init__(self, *args, **kwargs):
        """
        Create a Postgres handler instance.

        Because we need to do a client side copy, we will use a CLI connector
        for that as the only way to do it is for the client side copy to read
        from stdin. The COPY FILE and COPY PROGRAM options are really server
        side and require superuser priveleges.

        :param args:            As per super.
        :param kwargs:          As per super.
        """

        super().__init__(*args, **kwargs)

        self.cli_conn = get_cli_connection(
            conn_id=self.conn_spec['conn_id'],
            realm=self.realm,
            workdir=self.tmpdir,
            aws_session=self.aws_session,
        )

    # --------------------------------------------------------------------------
    def truncate_table(self, schema: str, table: str) -> None:
        """
        Truncate the specified table.

        Postgres seems to deadlock unless we commit after truncate. This is
        because we are using both the DBAPI 2.0 client as well as the psql
        client.

        :param schema:      Schema name
        :param table:       Table name

        """

        super().truncate_table(schema, table)
        self.conn.commit()

    # --------------------------------------------------------------------------
    def create_table(self, *args, **kwargs) -> None:
        """
        Create a table.

        For Postgres need to commit after create to avoid deadlock. This is
        because we are using both the DBAPI 2.0 client as well as the psql
        client.

        :param args:        As per super.
        :param kwargs:      As per super.

        """

        super().create_table(*args, **kwargs)
        self.conn.commit()

    # --------------------------------------------------------------------------
    def copy_from_s3(
        self,
        schema: str,
        table: str,
        bucket: str,
        key: str,
        region: str = None,
        copy_args: list[str] = None,
        load_columns: list[str] = None,
        s3_access_keys: dict[str, str] = None,
        iam_role: str = None,
        min_size: int = 0,
    ) -> list[str]:
        """
        Copy a file from S3 to Postgres with a client side COPY.

        There is also a degree of trickery here to support handling of
        manifests.

        :param schema:          Target schema name.
        :param table:           Target table names.
        :param copy_args:       Copy arguments. In addition to the standard
                                Postrges COPY args the following are also
                                supported: MANIFEST, GZIP
        :param bucket:          Source bucket name.
        :param key:             Source key in S3.
        :param region:          AWS region containing the bucket.
        :param load_columns:    A list of columns to load. May be empty which
                                means load all.
        :param s3_access_keys:  Not used.
        :param iam_role:        Not used.
        :param min_size:        Try to avoid loading data files below this size
                                in bytes.

        :return:                A list of strings indicating steps taken.

        """

        # ----------------------------------------
        # Validate COPY parameters.

        copy_args_dict = {p.split()[0].upper(): p for p in copy_args} if copy_args else {}
        bad_args = set(copy_args_dict) - self.COPY_PARAMS
        if bad_args:
            raise ValueError(f'Invalid COPY arguments: {", ".join(bad_args)}')

        # ----------------------------------------

        events = []

        s3_client = self.aws_session.client('s3')

        # ----------------------------------------
        # Prepare the copy params

        col_list = (
            '({})'.format(','.join([self.object_name(c.split(' ', 1)[0]) for c in load_columns]))
            if load_columns
            else ''
        )

        # Fake manifest handling
        if 'MANIFEST' in copy_args_dict:
            del copy_args_dict['MANIFEST']
            self.logger.debug(f'Reading manifest s3://{bucket}/{key}')
            events.append(f'Reading manifest s3://{bucket}/{key}')
            key_list = read_manifest(bucket, key)
        else:
            key_list = [(bucket, key)]

        gzipped = False
        if 'GZIP' in copy_args_dict:
            del copy_args_dict['GZIP']
            gzipped = True

        # Allow a non-standard * argument on the following options as a
        # shorthand for all columns.
        for k in 'FORCE_NULL', 'FORCE_NOT_NULL':
            if k in copy_args_dict:
                a = re.split(r'\s+', copy_args_dict[k], maxsplit=1)
                if len(a) == 2 and a[1].strip() == '*':
                    copy_args_dict[k] = '{} ({})'.format(
                        k, ', '.join(self.object_name(c) for c in self.columns(schema, table))
                    )

        copy_args_s = f'WITH ({", ".join(copy_args_dict.values())})' if copy_args else ''

        # ----------------------------------------
        # Prepare the COPY command.

        target = self.object_name(schema, table)
        sql_file = os.path.join(self.tmpdir, 'pg_load.sql')
        data_file = os.path.join(self.tmpdir, 'pg_load.dat')

        copy_cmd = fr"\copy {target}{col_list} FROM '{data_file}' {copy_args_s}"

        self.logger.debug('COPY command (%s): %s', sql_file, copy_cmd)

        # Create a little psql command file.
        with open(sql_file, 'w') as sqlfp:
            print(r'\set QUIET off', file=sqlfp)
            print(copy_cmd, file=sqlfp)

        # ----------------------------------------
        # Load our list of objects.

        events.append(f'Running COPY command(s) for {schema}.{table}')
        events.append(f'COPY command: {copy_cmd}')

        for b, k in key_list:
            # ------------------------------------
            # Skip runts

            if min_size:
                try:
                    file_info = s3_client.head_object(Bucket=b, Key=k)
                except Exception as e:
                    raise Exception(f's3://{b}/{k}: {e}')

                if file_info['ContentLength'] < min_size:
                    events.append(f'Skipping runt file s3://{b}/{k}')
                    continue

            # ------------------------------------
            # Download the file from S3. We use a fixed filename to avoid injection
            # problems from a problematic S3 key.

            download_file = data_file + '.gz' if gzipped else data_file
            try:
                s3_client.download_file(b, k, download_file)
                self.logger.debug(f'Downloaded s3://{b}/{k} to {download_file}')
            except Exception as e:
                raise Exception(f'Download failed: s3://{b}/{k} - {e}')

            # ------------------------------------
            # Uncompress the file

            if gzipped:
                try:
                    subprocess.check_output(
                        ['gunzip', download_file],
                        close_fds=True,
                        stdin=subprocess.DEVNULL,
                        stderr=subprocess.STDOUT,
                    )
                    self.logger.debug(f'Uncompressed {download_file}')
                except subprocess.CalledProcessError as e:
                    raise Exception(f'Gunzip failed with status {e.returncode}: {e.output}')

            # ------------------------------------
            # Do the COPY.

            events.append(f'Copying s3://{b}/{k}')

            # We can't use subprocess.check* because they don't terminate
            # child processes properly on timeout.

            timeout = config('PG_COPY_TIMEOUT', duration_to_seconds)
            with subprocess.Popen(
                [self.cli_conn, '-f', sql_file],
                close_fds=True,
                stdin=subprocess.DEVNULL,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                preexec_fn=os.setsid,
            ) as proc:
                try:
                    output = proc.communicate(timeout=timeout)[0]
                except subprocess.TimeoutExpired:
                    self.logger.warning(f'Sending SIGINT to process group {proc.pid}')
                    os.killpg(proc.pid, signal.SIGINT)
                    sleep(1)
                    try:
                        # Bring the hammer down
                        self.logger.warning(f'Sending SIGKILL to process group {proc.pid}')
                        os.killpg(proc.pid, signal.SIGKILL)
                    except ProcessLookupError:
                        pass
                    output = proc.communicate()[0]
                    raise subprocess.TimeoutExpired(proc.args, timeout, output)

            output = output.decode('utf-8').strip() if output else ''
            if proc.returncode:
                raise Exception(f'Status {proc.returncode}: {output}')

            events.append('Copy complete')
            events.append(output)

            # ------------------------------------
            # Clean up. Optional really -- lava will cleanup too.

            # noinspection PyBroadException
            try:
                unlink(data_file)
            except Exception as e:
                self.logger.warning(f'Could not unlink {data_file}: {e}')

        return events


# ------------------------------------------------------------------------------
@db_handler('redshift', 'redshift-serverless')
class Redshift(Database):
    """Model a Redshift database."""

    COPY_PARAMS = {
        # Note: NULL has to be specified as 'NULL AS' in the job spec.
        # Note: Credentials excluded - these are sourced from access keys/role.
        # Not supported: SSH
        'ACCEPTANYDATE',
        'ACCEPTINVCHARS',
        'AVRO',
        'BLANKSASNULL',
        'BZIP2',
        'COMPROWS',
        'COMPUPDATE',
        'CSV',
        'DATEFORMAT',
        'DELIMITER',
        'EMPTYASNULL',
        'ENCODING',
        'ENCRYPTED',
        'ESCAPE',
        'EXPLICIT_IDS',
        'FILLRECORD',
        'FIXEDWIDTH',
        'FORMAT',
        'GZIP',
        'IGNOREBLANKLINES',
        'IGNOREHEADER',
        'JSON',
        'LZOP',
        'MANIFEST',
        'MAXERROR',
        'NOLOAD',
        'NULL',
        'READRATIO',
        'REGION',
        'REMOVEQUOTES',
        'ROUNDEC',
        'SHAPEFILE',
        'STATUPDATE',
        'TIMEFORMAT',
        'TRIMBLANKS',
        'TRUNCATECOLUMNS',
        'ZSTD',
    }

    # --------------------------------------------------------------------------
    def table_is_empty(self, schema: str, table: str) -> bool:
        """
        Check if a given Redshift table is empty.

        For Redshift, a row count is ok to do this.

        :param schema:      Schema name
        :param table:       Table name

        :return:            True if the table is empty. False otherwise.

        """

        self.cursor.execute(f'SELECT COUNT(*) FROM {self.object_name(schema, table)}')  # noqa: S608
        return self.cursor.fetchone()[0] == 0

    # --------------------------------------------------------------------------
    def table_exists(self, schema: str, table: str) -> bool:
        """
        Check if a table (or view) exists.

        Visibility of table existence is dependent on the database access
        permissions of the user owning the connection.

        Works on any DB that supports the information_schema.

        We can't easily use query parameters without handling all the possible
        DBAPI 2.0 paramstyle settings. To reduce risk of injection, object
        names containing single quotes are rejected.

        :param schema:      Schema name.
        :param table:       Table name.

        :return:            True if the table exists.

        """

        if "'" in schema:
            raise ValueError(f'Bad schema name: {schema}')

        if "'" in table:
            raise ValueError(f'Bad table name: {table}')

        sql = f"""
            SELECT 1 FROM svv_tables
            WHERE table_catalog=CURRENT_DATABASE()
              AND table_schema='{schema}'
              AND table_name='{table}'
        """  # noqa: S608

        self.cursor.execute(sql)
        self.logger.debug('SQL: %s', sql)
        return bool(self.cursor.fetchone())

    # --------------------------------------------------------------------------
    def columns(self, schema: str, table: str) -> list[str]:
        """
        Get the column names for the given table.

        Works for external tables too. Results are cached.

        We can't easily use query parameters without handling all the possible
        DBAPI 2.0 paramstyle settings. To reduce risk of injection, object
        names containing single quotes are rejected.

        :param schema:      Schema name.
        :param table:       Table name.

        :return:            A list of column names.

        """

        if "'" in schema:
            raise ValueError(f'Bad schema name: {schema}')

        if "'" in table:
            raise ValueError(f'Bad table name: {table}')

        t = f'{schema}.{table}'

        if t not in self._columns:
            self.cursor.execute(
                f"""
                SELECT column_name FROM svv_columns
                WHERE table_catalog=CURRENT_DATABASE()
                  AND table_schema = '{schema}'
                  AND table_name = '{table}'
                  ORDER BY ordinal_position
                """  # noqa: S608
            )
            self._columns[t] = [row[0].lower() for row in self.cursor.fetchall()]

        return self._columns[t]

    # --------------------------------------------------------------------------
    def copy_from_s3(
        self,
        schema: str,
        table: str,
        bucket: str,
        key: str,
        region: str = None,
        copy_args: list[str] = None,
        load_columns: list[str] = None,
        s3_access_keys: dict[str, str] = None,
        iam_role: str = None,
        min_size: int = 0,
    ) -> list[str]:
        """
        Copy a file from S3 to a specific database table.

        No commit is done.

        :param schema:          Target schema name.
        :param table:           Target table names.
        :param copy_args:       Copy arguments.
        :param bucket:          Source bucket name.
        :param key:             Source key in S3.
        :param region:          AWS region containing the bucket.
        :param load_columns:    A list of columns to load. May be empty which
                                means load all.
        :param s3_access_keys:  Access keys to access S3.
        :param iam_role:        IAM role name to access S3. Some DBs use it, some
                                don't.
        :param min_size:        Try to avoid loading data files below this size
                                in bytes.

        :return:                A list of strings indicating steps taken.

        """

        # ----------------------------------------
        # Validate COPY parameters.

        copy_args_set = {p.split()[0].upper() for p in copy_args} if copy_args else set()
        bad_args = copy_args_set - self.COPY_PARAMS
        if bad_args:
            raise ValueError(f'Invalid COPY arguments: {", ".join(bad_args)}')

        events = []

        # ----------------------------------------
        # Skip runts

        if min_size:
            s3_client = self.aws_session.client('s3')
            try:
                file_info = s3_client.head_object(Bucket=bucket, Key=key)
            except Exception as e:
                raise Exception(f's3://{bucket}/{key}: {e}')

            if file_info['ContentLength'] < min_size:
                events.append(f'Skipping runt file s3://{bucket}/{key}')
                return events

        # ----------------------------------------
        # Prepare the copy command

        target = self.object_name(schema, table)
        copy_args = ' '.join(copy_args) if copy_args else ''
        col_list = (
            '({})'.format(','.join([self.object_name(c.split(' ', 1)[0]) for c in load_columns]))
            if load_columns
            else ''
        )

        copy_cmd = f"""
                COPY {target}{col_list} FROM 's3://{bucket}/{key}'
                {{authorization}}
                {copy_args}
                """

        # ----------------------------------------
        # Take care to not log secret credentials

        self.logger.debug(f'COPY command: {copy_cmd}')
        events.append(copy_cmd)
        copy_cmd = copy_cmd.format(
            authorization=redshift_authorization(iam_role, **(s3_access_keys or {}))
        )

        # ----------------------------------------
        # Run the COPY

        events.append(f'Running COPY command for {schema}.{table}')
        self.cursor.execute(copy_cmd)
        events.append(f'Copy to {schema}.{table} complete')

        return events


# ------------------------------------------------------------------------------
@db_handler('sqlite3')
class Sqlite3(Database):
    """Model an SQLite3 database."""

    COPY_PARAMS = {
        'DELIMITER',
        'DOUBLEQUOTE',
        'ESCAPECHAR',
        'GZIP',
        'HEADER',
        'MANIFEST',
        'QUOTECHAR',
        'QUOTING',
    }

    # --------------------------------------------------------------------------
    def truncate_table(self, schema: str, table: str) -> None:
        """
        Truncate the specified table.

        :param schema:      Schema name. Ignored for sqlite3.
        :param table:       Table name.

        """

        self.cursor.execute(f'DELETE FROM {self.object_name(table)}')  # noqa: S608
        self.conn.commit()
        self.cursor.execute('VACUUM')

    # --------------------------------------------------------------------------
    def create_table(self, schema: str, table: str, columns: list[str]) -> None:
        """
        Create a table.

        :param schema:      Schema name. Ignored for sqlite3.
        :param table:       Table name.
        :param columns:     A list of column specifications.

        """

        super().create_table('', table, columns)

    # --------------------------------------------------------------------------
    def drop_table(self, schema: str, table: str) -> None:
        """
        Drop a table.

        :param schema:      Schema name. Ignored for sqlite3.
        :param table:       Table name.

        """

        super().drop_table('', table)

    # --------------------------------------------------------------------------
    def table_is_empty(self, schema: str, table: str) -> bool:
        """
        Check if a given table is empty.

        :param schema:      Schema name. Ignored for sqlite3.
        :param table:       Table name.

        :return:            True if the table is empty. False otherwise.

        """

        return super().table_is_empty('', table)

    # --------------------------------------------------------------------------
    def table_exists(self, schema: str, table: str) -> bool:
        """
        Check if a table (or view) exists.

        :param schema:      Schema name. Ignored for sqlite3.
        :param table:       Table name.

        :return:            True if the table exists.

        """

        self.cursor.execute(
            "SELECT COUNT(*) FROM sqlite_master WHERE type='table' AND name=?", (table,)
        )

        return self.cursor.fetchone()[0] > 0

    # --------------------------------------------------------------------------
    def columns(self, schema: str, table: str) -> list[str]:
        """
        Get the column names for the given table.

        :param schema:      Schema name. Ignored for sqlite3.
        :param table:       Table name

        :return:            A list of column names.

        """

        if table not in self._columns:
            self.cursor.execute(f'PRAGMA table_info({self.object_name(table)})')
            self._columns[table] = [row[1] for row in self.cursor.fetchall()]

        return self._columns[table]

    # --------------------------------------------------------------------------
    def copy_from_s3(
        self,
        schema: str,
        table: str,
        bucket: str,
        key: str,
        region: str = None,
        copy_args: list[str] = None,
        load_columns: list[str] = None,
        s3_access_keys: dict[str, str] = None,
        iam_role: str = None,
        min_size: int = 0,
    ) -> list[str]:
        """
        Copy a file from S3 to a specific database table.

        No commit is done.

        :param schema:          Target schema name. Ignored for sqlite3.
        :param table:           Target table names.
        :param copy_args:       Copy arguments.
        :param bucket:          Source bucket name.
        :param key:             Source key in S3.
        :param region:          AWS region containing the bucket.
        :param load_columns:    A list of columns to load. May be empty which
                                means load all.
        :param s3_access_keys:  Access keys to access S3. Must be a dictionary
                                with aws_access_key_id and aws_secret_access_key.
        :param iam_role:        IAM role name to access S3. Some DBs use it, some
                                don't.
        :param min_size:        Try to avoid loading data files below this size
                                in bytes. Some subclasses may honour this.
                                Some not.

        :return:                A list of strings indicating steps taken.
        """

        copy_args_dict = {p.split()[0].upper(): p for p in copy_args} if copy_args else {}
        bad_args = set(copy_args_dict) - self.COPY_PARAMS
        if bad_args:
            raise ValueError(f'Invalid COPY arguments: {", ".join(bad_args)}')
        events = []

        # ----------------------------------------
        # Prepare the INSERT statement.

        if not load_columns:
            load_columns = self.columns(schema, table)
        column_count = len(load_columns)

        target = self.object_name(schema, table)

        insert_sql = 'INSERT INTO {target}({col_list}) VALUES ({placeholders})'.format(
            target=target,
            col_list=','.join(self.object_name(c.split(' ', 1)[0]) for c in load_columns),
            placeholders=','.join(column_count * '?'),
        )  # noqa: S608
        self.logger.debug('SQL: %s', insert_sql)

        # ----------------------------------------
        # Fake manifest handling

        if 'MANIFEST' in copy_args_dict:
            self.logger.debug(f'Reading manifest s3://{bucket}/{key}')
            events.append(f'Reading manifest s3://{bucket}/{key}')
            key_list = read_manifest(bucket, key)
        else:
            key_list = [(bucket, key)]

        _open = gzip.open if 'GZIP' in copy_args_dict else open
        fd, data_file = mkstemp(dir=self.tmpdir)
        os.close(fd)

        # ----------------------------------------
        # Setup CSV formatting args

        csv_format = {}

        for one_char_param in ('DELIMITER', 'ESCAPCHAR', 'QUOTECHAR'):
            if one_char_param in copy_args_dict:
                m = re.search(r" '(.)'$", copy_args_dict[one_char_param])
                if not m:
                    raise ValueError(
                        f'Bad {one_char_param} value: {copy_args_dict[one_char_param]}'
                    )
                csv_format[one_char_param.lower()] = m.group(1)

        if 'DOUBLEQUOTE' in copy_args_dict:
            csv_format['doublequote'] = True

        if 'QUOTING' in copy_args_dict:
            m = re.match(r"QUOTING\s+'([A-Z]+)'\s*$", copy_args_dict['QUOTING'], re.I)
            if not m:
                raise ValueError(f'Bad quoting spec: {copy_args_dict["QUOTING"]}')
            try:
                csv_format['quoting'] = getattr(csv, 'QUOTE_' + m.group(1).upper())
            except AttributeError:
                raise ValueError(f'Bad quoting style: {m.group(1)}')

        self.logger.debug('CSV format params: %s', csv_format)

        # ----------------------------------------
        # Load our list of objects.

        s3_client = self.aws_session.client('s3')

        events.append(f'Running INSERTs for {target}')

        for b, k in key_list:
            # ------------------------------------
            # Skip runts

            if min_size:
                try:
                    file_info = s3_client.head_object(Bucket=b, Key=k)
                except Exception as e:
                    raise Exception(f's3://{b}/{k}: {e}')

                if file_info['ContentLength'] < min_size:
                    events.append(f'Skipping runt file s3://{b}/{k}')
                    continue

            # ------------------------------------
            # Download the file from S3.

            try:
                s3_client.download_file(b, k, data_file)
                self.logger.debug(f'Downloaded s3://{b}/{k} to {data_file}')
            except Exception as e:
                raise Exception(f'Download failed: s3://{b}/{k} - {e}')

            # ------------------------------------
            # Read CSV and insert rows

            events.append(f'Inserting data from s3://{b}/{k}')

            try:
                with _open(data_file, 'rt') as fp:
                    csv_reader = csv.reader(fp, **csv_format)
                    row_num = 0

                    if 'HEADER' in copy_args_dict:
                        next(csv_reader, None)

                    for row in csv_reader:
                        row_num += 1
                        if len(row) != column_count:
                            raise Exception(
                                f's3://{b}/{k}: Expected {column_count} columns but got {len(row)}'
                            )

                        self.cursor.execute(insert_sql, row)
            finally:
                unlink(data_file)

            events.append(f'Inserted {row_num} rows from s3://{b}/{k}')

        return events


# ------------------------------------------------------------------------------
@db_handler('oracle')
class Oracle(Database):
    """Model an Oracle database."""

    COPY_PARAMS = {
        'DELIMITER',
        'DOUBLEQUOTE',
        'ESCAPECHAR',
        'GZIP',
        'HEADER',
        'MANIFEST',
        'QUOTECHAR',
        'QUOTING',
    }

    # Safe object names
    NAME_REGEX = re.compile(r'^[$#\w]+$', flags=re.I)

    # --------------------------------------------------------------------------
    def object_name(self, *name_part: str) -> str:
        """
        Sanitise a database object name.

        Oracle has funny rules around quoting -- it's not purely a syntax
        implication. If a column name is quoted at creation it always has to be
        quoted and vice versa. So its not safe here to just pop quotes around
        everything. Best we can do is just make sure names don't contain bad
        characters. This is not a fix-all solution but best we can do.

        :param name_part:   One or more name parts. Empty parts are silently
                            discarded.
        :return:            A clean object name composed of the parts.
        """

        for s in name_part:
            if not self.NAME_REGEX.match(s):
                raise ValueError(f'Bad database object name: {s}')

        return '.'.join(s for s in name_part if s)

    # --------------------------------------------------------------------------
    def table_is_empty(self, schema: str, table: str) -> bool:
        """
        Check if a given table is empty.

        :param schema:      Schema name.
        :param table:       Table name.

        :return:            True if the table is empty. False otherwise.

        """

        self.cursor.execute(
            f'SELECT 1 FROM {self.object_name(schema, table)} FETCH FIRST 1 ROWS ONLY'  # noqa: S608
        )
        return not self.cursor.fetchone()

    # --------------------------------------------------------------------------
    def table_exists(self, schema: str, table: str) -> bool:
        """
        Check if a table (or view) exists.

        Visibility of table existence is dependent on the database access
        permissions of the user owning the connection.


        :param schema:      Schema name. This is the table owner in Oracle.
        :param table:       Table name.

        :return:            True if the table exists.

        """

        self.cursor.execute(
            'SELECT 1 FROM all_tables WHERE UPPER(owner) = :sch AND UPPER(table_name) = :tbl',
            {'sch': schema.upper(), 'tbl': table.upper()},
        )

        return bool(self.cursor.fetchone())

    # --------------------------------------------------------------------------
    def drop_table(self, schema: str, table: str) -> None:
        """
        Drop a table.

        Oracle doesn't have a DROP TABLE IF EXISTS.

        :param schema:      Schema name.
        :param table:       Table name.

        """

        if self.table_exists(schema, table):
            self.cursor.execute(f'DROP TABLE {self.object_name(schema, table)}')
            self.logger.debug(f'Dropped table {schema}.{table}')
        else:
            self.logger.debug(f'Cannot drop {schema}.{table} - no such table')

    # --------------------------------------------------------------------------
    def columns(self, schema: str, table: str) -> list[str]:
        """
        Get the column names for the given table.

        :param schema:      Schema name. Ignored for sqlite3.
        :param table:       Table name

        :return:            A list of column names.

        """

        if table not in self._columns:
            self.cursor.execute(
                'SELECT column_name FROM all_tab_columns'
                ' WHERE UPPER(owner) = :sch AND UPPER(table_name) = :tbl'
                ' ORDER BY column_id',
                {'sch': schema.upper(), 'tbl': table.upper()},
            )

            self._columns[table] = [row[0] for row in self.cursor.fetchall()]

            if not self._columns[table]:
                raise Exception(f'{schema}.{table}: Cannot get columns')

        return self._columns[table]

    # --------------------------------------------------------------------------
    def copy_from_s3(
        self,
        schema: str,
        table: str,
        bucket: str,
        key: str,
        region: str = None,
        copy_args: list[str] = None,
        load_columns: list[str] = None,
        s3_access_keys: dict[str, str] = None,
        iam_role: str = None,
        min_size: int = 0,
    ) -> list[str]:
        """
        Copy a file from S3 to a specific database table.

        No commit is done.

        :param schema:          Target schema name.
        :param table:           Target table names.
        :param copy_args:       Copy arguments.
        :param bucket:          Source bucket name.
        :param key:             Source key in S3.
        :param region:          AWS region containing the bucket.
        :param load_columns:    A list of columns to load. May be empty which
                                means load all.
        :param s3_access_keys:  Access keys to access S3. Must be a dictionary
                                with aws_access_key_id and aws_secret_access_key.
        :param iam_role:        IAM role name to access S3. Some DBs use it, some
                                don't.
        :param min_size:        Try to avoid loading data files below this size
                                in bytes. Some subclasses may honour this.
                                Some not.

        :return:                A list of strings indicating steps taken.
        """

        copy_args_dict = {p.split()[0].upper(): p for p in copy_args} if copy_args else {}
        bad_args = set(copy_args_dict) - self.COPY_PARAMS
        if bad_args:
            raise ValueError(f'Invalid COPY arguments: {", ".join(bad_args)}')
        events = []

        # ----------------------------------------
        # Prepare the INSERT statement.

        if not load_columns:
            load_columns = self.columns(schema, table)
        column_count = len(load_columns)

        insert_sql = 'INSERT INTO {target}({col_list}) VALUES ({placeholders})'.format(
            target=self.object_name(schema, table),
            col_list=','.join(self.object_name(c.split(' ', 1)[0]) for c in load_columns),
            placeholders=','.join(f':v{n}' for n in range(1, column_count + 1)),
        )
        self.logger.debug('SQL: %s', insert_sql)

        # ----------------------------------------
        # Fake manifest handling

        if 'MANIFEST' in copy_args_dict:
            self.logger.debug(f'Reading manifest s3://{bucket}/{key}')
            events.append(f'Reading manifest s3://{bucket}/{key}')
            key_list = read_manifest(bucket, key)
        else:
            key_list = [(bucket, key)]

        _open = gzip.open if 'GZIP' in copy_args_dict else open
        fd, data_file = mkstemp(dir=self.tmpdir)
        os.close(fd)

        # ----------------------------------------
        # Setup CSV formatting args

        csv_format = {}

        for one_char_param in ('DELIMITER', 'ESCAPCHAR', 'QUOTECHAR'):
            if one_char_param in copy_args_dict:
                m = re.search(r" '(.)'$", copy_args_dict[one_char_param])
                if not m:
                    raise ValueError(
                        f'Bad {one_char_param} value: {copy_args_dict[one_char_param]}'
                    )
                csv_format[one_char_param.lower()] = m.group(1)

        if 'DOUBLEQUOTE' in copy_args_dict:
            csv_format['doublequote'] = True

        if 'QUOTING' in copy_args_dict:
            m = re.match(r"QUOTING\s+'([A-Z]+)'\s*$", copy_args_dict['QUOTING'], re.I)
            if not m:
                raise ValueError(f'Bad quoting spec: {copy_args_dict["QUOTING"]}')
            try:
                csv_format['quoting'] = getattr(csv, 'QUOTE_' + m.group(1).upper())
            except AttributeError:
                raise ValueError(f'Bad quoting style: {m.group(1)}')

        self.logger.debug('CSV format params: %s', csv_format)

        # ----------------------------------------
        # Load our list of objects.

        s3_client = self.aws_session.client('s3')

        events.append(f'Running INSERTs for {schema}.{table}')

        for b, k in key_list:
            # ------------------------------------
            # Skip runts

            if min_size:
                try:
                    file_info = s3_client.head_object(Bucket=b, Key=k)
                except Exception as e:
                    raise Exception(f's3://{b}/{k}: {e}')

                if file_info['ContentLength'] < min_size:
                    events.append(f'Skipping runt file s3://{b}/{k}')
                    continue

            # ------------------------------------
            # Download the file from S3.

            try:
                s3_client.download_file(b, k, data_file)
                self.logger.debug(f'Downloaded s3://{b}/{k} to {data_file}')
            except Exception as e:
                raise Exception(f'Download failed: s3://{b}/{k} - {e}')

            # ------------------------------------
            # Read CSV and insert rows

            events.append(f'Inserting data from s3://{b}/{k}')

            try:
                with _open(data_file, 'rt') as fp:
                    csv_reader = csv.reader(fp, **csv_format)
                    row_num = 0

                    if 'HEADER' in copy_args_dict:
                        next(csv_reader, None)

                    for row in csv_reader:
                        row_num += 1
                        if len(row) != column_count:
                            raise Exception(
                                f's3://{b}/{k}: Expected {column_count} columns but got {len(row)}'
                            )

                        self.cursor.execute(insert_sql, row)
            finally:
                unlink(data_file)

            events.append(f'Inserted {row_num} rows from s3://{b}/{k}')

        return events


# ------------------------------------------------------------------------------
@db_handler('mssql')
class MsSql(Database):
    """Model a Microsoft SQL Server database."""

    COPY_PARAMS = {
        'DELIMITER',
        'DOUBLEQUOTE',
        'ESCAPECHAR',
        'GZIP',
        'HEADER',
        'MANIFEST',
        'QUOTECHAR',
        'QUOTING',
    }

    ANSI_QUOTES = False

    # --------------------------------------------------------------------------
    def __init__(self, *args, **kwargs):
        """Init."""

        super().__init__(*args, **kwargs)

        self.quotes = '"' if self.ANSI_QUOTES else '[]'

    # --------------------------------------------------------------------------
    def table_is_empty(self, schema: str, table: str) -> bool:
        """
        Check if a given table is empty.

        For MsSQL, a simple row count is a really bad idea on big tables.

        :param schema:      Schema name.
        :param table:       Table name.

        :return:            True if the table is empty. False otherwise.

        """

        sql = f'SELECT TOP 1 1 FROM {self.object_name(schema, table)}'  # noqa: S608
        self.logger.debug('SQL: %s', sql)
        self.cursor.execute(sql)
        return not self.cursor.fetchone()

    # --------------------------------------------------------------------------
    def copy_from_s3(
        self,
        schema: str,
        table: str,
        bucket: str,
        key: str,
        region: str = None,
        copy_args: list[str] = None,
        load_columns: list[str] = None,
        s3_access_keys: dict[str, str] = None,
        iam_role: str = None,
        min_size: int = 0,
    ) -> list[str]:
        """
        Copy a file from S3 to a specific database table.

        No commit is done.

        :param schema:          Target schema name.
        :param table:           Target table names.
        :param copy_args:       Copy arguments.
        :param bucket:          Source bucket name.
        :param key:             Source key in S3.
        :param region:          AWS region containing the bucket.
        :param load_columns:    A list of columns to load. May be empty which
                                means load all.
        :param s3_access_keys:  Access keys to access S3. Must be a dictionary
                                with aws_access_key_id and aws_secret_access_key.
        :param iam_role:        IAM role name to access S3. Some DBs use it, some
                                don't.
        :param min_size:        Try to avoid loading data files below this size
                                in bytes. Some subclasses may honour this.
                                Some not.

        :return:                A list of strings indicating steps taken.
        """

        copy_args_dict = {p.split()[0].upper(): p for p in copy_args} if copy_args else {}
        bad_args = set(copy_args_dict) - self.COPY_PARAMS
        if bad_args:
            raise ValueError(f'Invalid COPY arguments: {", ".join(bad_args)}')
        events = []

        # ----------------------------------------
        # Prepare the INSERT statement.

        if not load_columns:
            load_columns = self.columns(schema, table)
        column_count = len(load_columns)

        # pyodbc uses qmark paramstyle
        insert_sql = 'INSERT INTO {target}({col_list}) VALUES ({placeholders})'.format(
            target=self.object_name(schema, table),
            col_list=','.join(self.object_name(c.split(' ', 1)[0]) for c in load_columns),
            placeholders=','.join('?' * column_count),
        )
        self.logger.debug('SQL: %s', insert_sql)

        # ----------------------------------------
        # Fake manifest handling

        if 'MANIFEST' in copy_args_dict:
            self.logger.debug(f'Reading manifest s3://{bucket}/{key}')
            events.append(f'Reading manifest s3://{bucket}/{key}')
            key_list = read_manifest(bucket, key)
        else:
            key_list = [(bucket, key)]

        _open = gzip.open if 'GZIP' in copy_args_dict else open
        fd, data_file = mkstemp(dir=self.tmpdir)
        os.close(fd)

        # ----------------------------------------
        # Setup CSV formatting args

        csv_format = {}

        for one_char_param in ('DELIMITER', 'ESCAPCHAR', 'QUOTECHAR'):
            if one_char_param in copy_args_dict:
                m = re.search(r" '(.)'$", copy_args_dict[one_char_param])
                if not m:
                    raise ValueError(
                        f'Bad {one_char_param} value: {copy_args_dict[one_char_param]}'
                    )
                csv_format[one_char_param.lower()] = m.group(1)

        if 'DOUBLEQUOTE' in copy_args_dict:
            csv_format['doublequote'] = True

        if 'QUOTING' in copy_args_dict:
            m = re.match(r"QUOTING\s+'([A-Z]+)'\s*$", copy_args_dict['QUOTING'], re.I)
            if not m:
                raise ValueError(f'Bad quoting spec: {copy_args_dict["QUOTING"]}')
            try:
                csv_format['quoting'] = getattr(csv, 'QUOTE_' + m.group(1).upper())
            except AttributeError:
                raise ValueError(f'Bad quoting style: {m.group(1)}')

        self.logger.debug('CSV format params: %s', csv_format)

        # ----------------------------------------
        # Load our list of objects.

        s3_client = self.aws_session.client('s3')

        events.append(f'Running INSERTs for {schema}.{table}')

        for b, k in key_list:
            # ------------------------------------
            # Skip runts

            if min_size:
                try:
                    file_info = s3_client.head_object(Bucket=b, Key=k)
                except Exception as e:
                    raise Exception(f's3://{b}/{k}: {e}')

                if file_info['ContentLength'] < min_size:
                    events.append(f'Skipping runt file s3://{b}/{k}')
                    continue

            # ------------------------------------
            # Download the file from S3.

            try:
                s3_client.download_file(b, k, data_file)
                self.logger.debug(f'Downloaded s3://{b}/{k} to {data_file}')
            except Exception as e:
                raise Exception(f'Download failed: s3://{b}/{k} - {e}')

            # ------------------------------------
            # Read CSV and insert rows

            events.append(f'Inserting data from s3://{b}/{k}')

            try:
                with _open(data_file, 'rt') as fp:
                    csv_reader = csv.reader(fp, **csv_format)
                    row_num = 0

                    if 'HEADER' in copy_args_dict:
                        next(csv_reader, None)

                    for row in csv_reader:
                        row_num += 1
                        if len(row) != column_count:
                            raise Exception(
                                f's3://{b}/{k}: Expected {column_count} columns but got {len(row)}'
                            )

                        self.cursor.execute(insert_sql, row)
            finally:
                unlink(data_file)

            events.append(f'Inserted {row_num} rows from s3://{b}/{k}')

        return events


# ..............................................................................
# region Redshift
# ..............................................................................


# ------------------------------------------------------------------------------
def redshift_oid(cursor, schema: str, relation: str) -> int:
    """
    Get the OID for the specified relation.

    :param cursor:      Database cursor.
    :param schema:      Schema name.
    :param relation:    Relation (table or view) name.

    :return:            The OID of the object or None if the object doesn't
                        exist.

    """

    sql = """
            SELECT c.oid from pg_catalog.pg_class c
            LEFT JOIN pg_catalog.pg_namespace n ON n.oid = c.relnamespace
            WHERE n.nspname = %s AND c.relname = %s
    """

    cursor.execute(sql, (schema.lower(), relation.lower()))
    result = cursor.fetchall()
    return int(result[0][0]) if result else None


# ------------------------------------------------------------------------------
@deprecated('Use `redshift_get_column_info2()` instead')
def redshift_get_column_info(cursor, schema: str, relation: str) -> list[tuple[str, ...]]:
    """
    Get column information for the specified relation.

    !!! warning "Deprecated as of v7.1.0"
       This will not work for views with no schema binding or external (data
       share) tables. Use `redshift_get_column_info2()` instead.

    :param cursor:      Database cursor.
    :param schema:      Schema name.
    :param relation:    Relation (table or view) name.

    :return:            A list of tuples (column name, type) with all components
                        guaranteed to be in lower case.


    :raise Exception:   If the relation doesn't exist.

    """

    oid = redshift_oid(cursor, schema, relation)

    if oid is None:
        raise Exception(f'Cannot get column info for {schema}.{relation}')

    sql = """
        SELECT LOWER(a.attname),
               LOWER(pg_catalog.format_type(a.atttypid, a.atttypmod))
        FROM pg_catalog.pg_attribute a
        WHERE a.attrelid = %s AND a.attnum > 0 AND NOT a.attisdropped
        ORDER BY a.attnum
    """

    cursor.execute(sql, (oid,))
    return [(row[0], row[1]) for row in cursor.fetchall() if row]


# ------------------------------------------------------------------------------
def redshift_get_column_info2(cursor, schema: str, relation: str) -> tuple[list[str]]:
    """
    Get column information for the specified relation in the current database.

    This does handle views with no schema binding and external (data share)
    tables.

    !!! info
       This produces similar but slightly different output to that produced by
       `redshift_get_column_info()`. For example, this version does not include
       text field lengths. It also produces a tuple of lists instead of a list
       of tuples. In most cases the differences are not significant.

    !!! info
       Expects a `format` paramstyle on the driver (e.g. pg8000).

    :param cursor:      Database cursor.
    :param schema:      Schema name.
    :param relation:    Relation (table or view) name.

    :return:            A tuple of 2 element lists [column name, type].

    :raise Exception:   If the column information cannot be obtained.
    """

    sql = """
        SELECT column_name, LOWER(data_type) FROM svv_columns
        WHERE table_catalog=CURRENT_DATABASE() AND table_schema=%s AND table_name=%s
        ORDER by ordinal_position
    """

    cursor.execute(sql, (schema, relation))
    columns = cursor.fetchall()
    if not columns:
        raise Exception(f'Cannot get column info for {schema}.{relation}')

    return columns


# ------------------------------------------------------------------------------
def redshift_authorization(
    s3_iam_role: str = None,
    aws_access_key_id: str = None,
    aws_secret_access_key: str = None,
    aws_session_token: str = None,
    **_,
) -> str:
    """
    Prepare authorization parameters for external resource access (e.g. S3).

    This is suitable for COPY and UNLOAD.

    :param s3_iam_role: An IAM role name. Either this or the two access key
                        parameters must be provided. The role is preferred.
    :param aws_access_key_id: AWS access key.
    :param aws_secret_access_key: AWS access secret key.
    :param aws_session_token: AWS session token.

    :return:    :An S3 credentials string for use in Redshift UNLOAD.
    """
    ...

    for s in (s3_iam_role, aws_access_key_id, aws_secret_access_key, aws_session_token):
        if s and "'" in s:
            raise ValueError('Bad Redshift authorization component: must not contain quotes')

    if s3_iam_role:
        return f"IAM_ROLE '{s3_iam_role}'"

    if not all((aws_access_key_id, aws_secret_access_key)):
        raise ValueError('Either IAM role or access keys required')

    auth = [
        'ACCESS_KEY_ID',
        f"'{aws_access_key_id}'",
        'SECRET_ACCESS_KEY',
        f"'{aws_secret_access_key}'",
    ]
    if aws_session_token:
        auth.extend(['SESSION_TOKEN', f"'{aws_session_token}'"])
    return ' '.join(auth)


# ..............................................................................
# endregion Redshift
# ..............................................................................


# ..............................................................................
# region Miscellaneous DB utils
# ..............................................................................


# ------------------------------------------------------------------------------
def begin_transaction(conn, cursor=None) -> None:
    """
    Begin a transaction, trying to navigate the vagaries of DBAPI 2.0.

    DBAPI 2.0 has no consistent interface for beginning a transaction. Try to
    do this in a DB agnostic way.

    :param conn:        An open DBAPI database connector.
    :param cursor:      An optional DB cursor. If not supplied one will be
                        created if required.

    """

    try:
        # Plan A. Works for cx_Oracle and pymysql
        # Won't work for pg8000 or SQLite3 but plan C should.
        conn.begin()
    except AttributeError:
        try:
            # Plan B. Won't work for SQLite3 but plan C should.
            conn.autocommit = False
        except AttributeError:
            # Plan C. Won't work for Oracle but plan A and/or B should.
            if not cursor:
                cursor = conn.cursor()
            cursor.execute('BEGIN')


# ------------------------------------------------------------------------------
def query_to_dict(cursor, *args, **kwargs) -> Iterator[dict]:
    """
    Run a query on the given cursor and stream the results back in dict format.

    :param cursor:  Database cursor.
    :param args:    Passed to cursor.execute().
    :param kwargs:  Passed to cursor.execute().

    :return:        An iterator of dictionaries keyed on column name.
    """

    cursor.execute(*args, **kwargs)
    column_names = tuple(c[0] for c in cursor.description)

    while True:
        if not (batch := cursor.fetchmany()):
            break

        for row in batch:
            yield dict(zip(column_names, row))


# ..............................................................................
# endregion Miscellaneous DB utils
# ..............................................................................
