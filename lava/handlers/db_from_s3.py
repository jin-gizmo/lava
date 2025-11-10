"""
Copy data from S3 to a database.

There is nothing database specific in here provided the target database supports
some very simple SQL constructs. All of the database specific stuff is in
lava.lib.db.

The original logic in here was derived from the rsDroploader2 code but has been
generalised to handle multiple database types.

"""

from __future__ import annotations

import logging
import re
from typing import Any

import boto3
import jinja2

from lava.config import LOGNAME
from lava.connection import get_aws_connection, get_connection_spec
from lava.connection.core import make_application_name
from lava.lavacore import LavaError, jinja_render_vars
from lava.lib.aws import s3_object_exists
from lava.lib.db import Database
from lava.lib.misc import dict_check, size_to_bytes, splitext2, str2bool

__author__ = 'Murray Andrews'

LOG = logging.getLogger(name=LOGNAME)

JOB_PARAMS_REQUIRED_FIELDS = {
    'db_conn_id',
    'bucket',
    'key',
    'schema',
    'table',
    'mode',
}

JOB_PARAMS_OPTIONAL_FIELDS = {
    'args',
    'columns',
    'jinja',
    's3_conn_id',
    's3_iam_role',
    'skip_missing',
    'vars',
    'min_size',
}

COPY_MODES = {'truncate', 'drop', 'append', 'abort', 'switch', 'delete'}


# ------------------------------------------------------------------------------
# noinspection PyUnusedLocal
def run(
    job_spec: dict[str, Any],
    realm_info: dict[str, Any],
    tmpdir: str,
    s3tmp: str,
    dev_mode: bool = False,
    aws_session: boto3.Session = None,
) -> dict[str, Any]:
    """
    Copy a data set from S3 to a database.

    Allowed job parameters are (* means optional):

    - args*
        Database specific arguments used in the copy process.

    - bucket
        Source bucket.

    - columns*
        A list of SQL column specifications.

    - db_conn_id
        A connectiion ID for the target DB.

    - jinja*
        An optional boolean indicating whether Jinja rendering is enabled.
        Default True.

    - key
        Source S3 key.

    - mode
        Update mode for the target table.

    - s3_conn_id*
        A connection ID for S3. Some DBs need it. Some don't.

    - s3_iam_role*
        IAM role to access S3. Some DBs need it. Some don't.

    - schema
        Target schema.

    = skip_missing
        By default, trying to load a non-existent file will result in an error.
        If this boolean is true, then no attempt is made to load missing files.
        Note that this won't help in the situation where the file is removed
        from S3 between the check for existence and the database load operation.

    - table
        Target table.

    - vars*
        A map of variables injected when jinja rendering is done.

    Note that individual target types may allow or require additional params.

    :param job_spec:        The job spec from the DynamoDB database.
    :param realm_info:      Realm specific parameters.
    :param tmpdir:          A local temporary directory.
    :param s3tmp:           A prefix in S3 where temporary assets can be created
                            and left for others to pick up for limited time.
    :param dev_mode:        Not used for this handler.
    :param aws_session:     A boto3 Session().

    :return:                A dictionary of parameters that are available to
                            on-success, on-error, on-retry handlers.
    """

    if not aws_session:
        aws_session = boto3.Session()

    # ----------------------------------------
    # Validate job parameters.

    parameters = job_spec['parameters']
    try:
        dict_check(
            parameters, required=JOB_PARAMS_REQUIRED_FIELDS, optional=JOB_PARAMS_OPTIONAL_FIELDS
        )
    except ValueError as e:
        raise LavaError(f'Bad job parameters: {e}')

    if parameters['mode'] not in COPY_MODES:
        raise LavaError(f'Bad mode: {parameters["mode"]}')

    parameters['min_size'] = size_to_bytes(parameters.get('min_size', 0))

    # ----------------------------------------
    # Prepare for Jinja rendering

    job_vars = parameters.get('vars', {})
    if not isinstance(job_vars, dict):
        raise LavaError('vars must be a map/dict')
    enable_jinja = parameters.get('jinja', True)
    render_vars = jinja_render_vars(job_spec, realm_info, vars=job_vars)

    # ----------------------------------------
    # Render the bucket and key

    s3_bucket = parameters['bucket']
    s3_key = parameters['key']

    if enable_jinja:
        s3_bucket = jinja2.Template(s3_bucket).render(**render_vars)
        s3_key = jinja2.Template(s3_key).render(**render_vars)

    LOG.debug(f'Copy source is s3://{s3_bucket}/{s3_key}')

    return_info = {'exit_status': 0, 'bucket': s3_bucket, 'key': s3_key}

    if str2bool(parameters.get('skip_missing', False)):
        try:
            obj_exists = s3_object_exists(s3_bucket, s3_key, aws_session=aws_session)
        except Exception as e:
            raise LavaError(f's3://{s3_bucket}/{s3_key} - {e}')
        if not obj_exists:
            LOG.info('Object s3://%s/%s does not exist - skipping', s3_bucket, s3_key)
            return_info['events'] = ['Skipped missing object']
            if dev_mode:
                print('\n'.join(return_info['events']))
            return return_info

    # ----------------------------------------
    # Render the schema and table

    if enable_jinja:
        render_vars['bucket'] = s3_bucket
        render_vars['key'] = s3_key
        for key in 'table', 'schema':
            parameters[key] = jinja2.Template(parameters[key]).render(**render_vars)

    # ----------------------------------------
    # Target schema and table name can be derived from the S3 object key

    # If key is a/b/c.x.y -- we want the "a/b/c" part
    data_object_nosuffix = splitext2(s3_key, pathsep='/', extsep='.')[0]

    for key in 'table', 'schema':
        # Look for search patterns in table and schema names
        if parameters[key].startswith('/'):
            # It's a regex
            pat = parameters[key][1:]  # Remove leading /
            LOG.debug(
                f'Matching object name {data_object_nosuffix} against pattern {pat} to get {key}'
            )

            m = re.search(pat, data_object_nosuffix)
            if not m:
                raise LavaError(f'Object name {data_object_nosuffix} does not match {key} regex')
            try:
                parameters[key] = m.group(1).lower()
                LOG.debug(f'Setting {key} to {parameters[key]}')
            except IndexError:
                raise LavaError(f'Regex for {key} does not contain a capture group')
        parameters[key] = parameters[key].lower()

    # ----------------------------------------
    # Get connection details for S3. Different DBs consume these differently.

    s3_conn_id = parameters.get('s3_conn_id')
    if s3_conn_id:
        s3_access_keys = get_aws_connection(s3_conn_id, job_spec['realm'], aws_session=aws_session)
    else:
        s3_access_keys = None

    # ----------------------------------------
    # Create a handler for the database

    conn_spec = get_connection_spec(
        parameters['db_conn_id'], job_spec['realm'], aws_session=aws_session
    )

    try:
        db_handler = Database.handler(
            db_type=conn_spec['type'],
            conn_spec=conn_spec,
            realm=job_spec['realm'],
            tmpdir=tmpdir,
            aws_session=aws_session,
            logger=LOG,
            application_name=make_application_name(
                conn_id=parameters['db_conn_id'], realm=job_spec['realm'], job_id=job_spec['job_id']
            ),
        )
    except KeyError:
        raise LavaError(f'db_from_s3 does not support {conn_spec["type"]} databases')

    LOG.debug(f'Found a handler for db type: {conn_spec["type"]}')

    copy_handler = copy_switch if parameters['mode'] == 'switch' else copy_simple

    # ----------------------------------------
    # Invoke the copy handler

    try:
        return_info['events'] = copy_handler(
            db=db_handler,
            bucket=s3_bucket,
            key=s3_key,
            region=s3_access_keys['region'] if s3_access_keys else aws_session.region_name,
            job_spec=job_spec,
            s3_access_keys=s3_access_keys,
            iam_role=parameters.get('s3_iam_role'),
        )
    except Exception as e:
        return_info['exit_status'] = 1
        return_info['error'] = str(e)
        raise LavaError(f'Copy failed: {e}', data=return_info)
    finally:
        db_handler.close()

    if dev_mode:
        print('\n'.join(return_info['events']))

    return return_info


# --------------------------------------------------------------------------
def copy_simple(
    db: Database,
    bucket: str,
    key: str,
    region: str,
    job_spec: dict[str, Any],
    s3_access_keys: dict[str, Any],
    iam_role: str,
) -> list[str]:
    """
    Handle copy modes truncate, delete, drop, append and abort.

    :param db:              A database handler.
    :param bucket:          Bucket name.
    :param key:             Data object name.
    :param region:          AWS region containing the bucket.
    :param job_spec:        Job specification.
    :param s3_access_keys:  Access keys to access S3. Must be a dictionary
                            with aws_access_key_id and aws_secret_access_key.
    :param iam_role:        IAM role name to access S3. Some DBs use it, some
                            don't.

    :return:                A list of informational messages.
    """

    events = []
    parameters = job_spec['parameters']
    schema = parameters['schema']  # type: str
    table = parameters['table']  # type: str
    mode = parameters['mode']
    # Fully qualified table name
    table_fqn = db.object_name(schema, table)

    # ----------------------------------------
    # Check if the target table exists.

    LOG.debug(f'Checking if table {table_fqn} exists')
    table_exists = db.table_exists(schema, table)

    # ----------------------------------------
    # Prepare the data table
    if mode == 'abort':
        if table_exists:
            raise LavaError(f'Table {table_fqn} already exists')
    elif mode == 'delete':
        if table_exists:
            events.append(f'Deleting from table {table_fqn}')
            db.cursor.execute(f'DELETE FROM {table_fqn}')
            events.append(f'Deleted from table {table_fqn}')
    elif mode == 'truncate':
        if table_exists:
            events.append(f'Truncating table {table_fqn}')
            db.truncate_table(schema, table)
            events.append(f'Truncated table {table_fqn}')
    elif mode == 'drop':
        if table_exists:
            events.append(f'Dropping table {table_fqn}')
            db.drop_table(schema, table)
            events.append(f'Dropped table {table_fqn}')
            table_exists = False
    elif mode == 'append':
        pass
    else:
        raise LavaError(f'Internal error: Bad mode: {mode}')

    columns = parameters.get('columns')
    if not table_exists:
        # Need to create the table
        if not columns:
            raise LavaError(
                f'Table {table_fqn} doesn\'t exist and no column spec provided to create it'
            )

        events.append(f'Creating table {table_fqn}')
        db.create_table(schema, table, columns)
        events.append(f'Created table {table_fqn}')

    # ----------------------------------------
    # Do the copy

    events.extend(
        db.copy_from_s3(
            schema=schema,
            table=table,
            bucket=bucket,
            key=key,
            region=region,
            copy_args=parameters.get('args'),
            load_columns=parameters.get('columns'),
            s3_access_keys=s3_access_keys,
            iam_role=iam_role,
            min_size=parameters.get('min_size', 0),
        )
    )

    db.conn.commit()
    events.append(f'Commit {table_fqn}')

    return events


# --------------------------------------------------------------------------
def copy_switch(
    db: Database,
    bucket: str,
    key: str,
    region: str,
    job_spec: dict[str, Any],
    s3_access_keys: dict[str, Any],
    iam_role: str,
) -> list[str]:
    """
    Handle copy mode `switch` which alternates between two A and B tables.

    If the user specifies table name x then the actual tables that are used
    are x_a and x_b. One of them must be empty.

    :param db:              A database handler.
    :param bucket:          Bucket name.
    :param key:             Data object name.
    :param region:          AWS region containing the bucket.
    :param job_spec:        Job specification.
    :param s3_access_keys:  Access keys to access S3. Must be a dictionary
                            with aws_access_key_id and aws_secret_access_key.
    :param iam_role:        IAM role name to access S3. Some DBs use it, some
                            don't.

    :return:                A list of informational messages.
    """

    events = []
    parameters = job_spec['parameters']
    schema = parameters['schema']  # type: str
    table = parameters['table']  # type: str
    # Fully qualified table name
    table_fqn = f'{schema}.{table}' if schema else table
    columns = parameters.get('columns')

    # ----------------------------------------
    # Check if the target tables exist and that one of them is empty.

    table_new = None  # Data will get loaded in here
    table_old = None  # This one will be emptied after
    table_old_fqn = None

    for new, old in ('a', 'b'), ('b', 'a'):
        t = table + '_' + new
        t_fqn = f'{schema}.{t}' if schema else t

        LOG.debug(f'Checking if table {t_fqn} exists')
        if not db.table_exists(schema, t):
            # Need to create the table
            if not columns:
                raise LavaError(
                    f'Table {t_fqn} doesn\'t exist and no column spec provided to create it'
                )

            events.append(f'Creating table {t_fqn}')
            db.create_table(schema, t, columns)
            events.append(f'Created table {t_fqn}')

        if not table_new and db.table_is_empty(schema, t):
            events.append(f'Table {t_fqn} is empty - setting as load target')
            table_new = t
            table_old = table + '_' + old
            table_old_fqn = f'{schema}.{table_old}' if schema else table_old

    if not table_new:
        raise LavaError(f'Neither A nor B switch table is empty for {table_fqn}')

    # At this point the A and B tables exist and table_new is empty.

    # ----------------------------------------
    # Do the copy

    events.extend(
        db.copy_from_s3(
            schema=schema,
            table=table_new,
            bucket=bucket,
            key=key,
            region=region,
            copy_args=parameters.get('args'),
            load_columns=parameters.get('columns'),
            s3_access_keys=s3_access_keys,
            iam_role=iam_role,
            min_size=parameters.get('min_size', 0),
        )
    )

    # ----------------------------------------
    # Now empty the old table.

    events.append(f'Deleting from table {table_old_fqn}')
    db.cursor.execute(f'DELETE FROM {table_old_fqn}')
    events.append(f'Deleted from table {table_old_fqn}')

    # ----------------------------------------
    # Commit the changes and then TRUNCATE the old table. Note that TRUNCATE
    # may also commit any transaction of which it is a part.

    db.conn.commit()
    events.append(f'Commit {table_fqn}')

    events.append(f'Truncating table {table_old_fqn}')
    db.truncate_table(schema, table_old)
    events.append(f'Truncated table {table_old_fqn}')

    return events
