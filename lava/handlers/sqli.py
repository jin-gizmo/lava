"""SQL (inline) handler."""

from __future__ import annotations

import csv
import logging
import os
from typing import Any

import boto3
import jinja2
import sqlparse

from lava.config import LOGNAME, config
from lava.connection import get_pysql_connection
from lava.connection.core import make_application_name
from lava.lavacore import LavaError, jinja_render_vars
from lava.lib.aws import s3_split, s3_upload
from lava.lib.db import begin_transaction
from lava.lib.misc import dict_check, str2bool
from .sql import JOB_PARAMS_OPTIONAL_FIELDS, JOB_PARAMS_REQUIRED_FIELDS, OUTPUT_PARAM_RE

__author__ = 'Murray Andrews'

LOG = logging.getLogger(name=LOGNAME)


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
    Run an SQL payload specified inline in the payload.

    Unlike the `sql` job type that gets its payload from S3, the sqli job has
    its SQL inline in the payload as a string or list.

    The output is dropped in the s3tmp area.

    Allowed job parameters are:

    - conn_id
        A connectiion ID for the target DB. Requird.

    - transaction
        If True, the sequence of SQLs is run within a transaction.
        Default False.

    - jinja
        An optional boolean indicating whether Jinja rendering is enabled.
        Default True.

    - header
        If True, add a header for SELECT outputs.

    - output
       SELECT output is placed in this directory locally and in s3_temp.
       Must be alphanumeric.

    - raw
        By default, an attempt will be made to split each payload file into
        individual SQL statements. This should be safe in most cases. To
        suppress this behaviour and run the payload as-is, set raw to True.

    - vars
        An optional dictionary of variables to use when Jinja rendering the SQL.

    Optional CSV formatting parameters:

    - delimiter
        Field delimiter. Default '|'

    - dialect
        As for csv.writer. Default excel.

    - doublequote
        As for csv.writer. Default False.

    - escapechar
        As for csv.writer. Default None.

    - quotechar
        As for csv.writer. Default '"'.

    - quoting
        As for csv.writer ``QUOTE_`` parameters (without the ``QUOTE_`` prefix).
        Default "minimal" (QUOTE_MINIMAL).


    :param job_spec:        The job spec from the DynamoDB database.
    :param realm_info:      Realm specific parameters.
    :param tmpdir:          A local temporary directory.
    :param s3tmp:           A prefix in S3 where temporary assets can be created
                            and left for others to pick up for limited time.
    :param dev_mode:        Not used for this handler.
    :param aws_session:     A boto3 Session()

    :return:                A dictionary of parameters that are available to
                            on-success, on-error, on-retry handlers.

    """

    parameters = job_spec['parameters']

    try:
        dict_check(
            parameters, required=JOB_PARAMS_REQUIRED_FIELDS, optional=JOB_PARAMS_OPTIONAL_FIELDS
        )
    except ValueError as e:
        raise LavaError(f'Bad job parameters: {e}')

    quoting_style = parameters.get('quoting', config('SQL_QUOTING')).upper()
    try:
        quoting = getattr(csv, 'QUOTE_' + quoting_style)
    except AttributeError:
        raise LavaError(f'Bad quoting style: {quoting_style}')

    datadir = []
    if 'output' in parameters:
        datadir = [parameters['output']]
        if not OUTPUT_PARAM_RE.match(datadir[0]):
            raise LavaError('Bad output parameter: Must be alphanumeric')

    transaction = parameters.get('transaction', False)
    raw = parameters.get('raw', False)

    job_vars = parameters.get('vars', {})
    if not isinstance(job_vars, dict):
        raise LavaError('vars must be a map/dict')
    enable_jinja = parameters.get('jinja', True)
    render_vars = jinja_render_vars(job_spec, realm_info, vars=job_vars)

    if not aws_session:
        aws_session = boto3.Session()

    # ----------------------------------------
    # Get connection for the target DB

    conn_id = parameters['conn_id']
    conn = get_pysql_connection(
        conn_id,
        job_spec['realm'],
        autocommit=not transaction,
        aws_session=aws_session,
        application_name=make_application_name(
            conn_id=conn_id, realm=job_spec['realm'], job_id=job_spec['job_id']
        ),
    )
    try:
        LOG.debug('Autocommit set to %s', conn.autocommit)
    except AttributeError:
        LOG.debug('Autocommit not supported for connector %s', conn_id)

    cursor = conn.cursor()
    return_info = {'exit_status': 0, 'output': {}}
    try:
        batch_size = int(parameters.get('batch_size', config('SQL_BATCH_SIZE', int)))
        if batch_size < 1:
            raise ValueError('Must be >= 1')
    except Exception as e:
        raise LavaError(f'Bad batch_size: {e}')

    # ----------------------------------------
    payload = job_spec['payload']
    if isinstance(payload, str):
        payload = [payload]
    elif not isinstance(payload, list):
        raise LavaError('Bad payload: must be string or list of strings')

    try:
        if transaction:
            LOG.debug('Starting transaction')
            begin_transaction(conn, cursor)

        for payload_num, sql_text in enumerate(payload):
            # Get ready for a list of output files.
            return_info['output'][f'{payload_num}'] = []

            LOG.debug('Raw SQL: %d: %s', payload_num, sql_text)

            # ----------------------------------------
            # Split up the payload into statements unless raw
            sql_statements = [sql_text] if raw else sqlparse.split(sql_text.strip())

            for n, sql in enumerate(sql_statements):
                LOG.debug('Preparing SQL %d: %s', n, sql)

                # ------------------------------------
                # Render the SQL using Jinja and run it

                if enable_jinja:
                    sql = jinja2.Template(sql).render(**render_vars)
                    LOG.debug('Rendered SQL %d: %s', n, sql)

                # Remove any trailing whitespace and semi-colon. This should be
                # ok for most DBAPI 2.0 and some of them insist on it.
                sql = sql.strip().rstrip(';')

                if not sql:
                    LOG.debug('Skipping empty SQL statement # %d', n)
                    continue

                cursor.execute(sql)

                # ------------------------------------
                # Query succeeded - capture output but only if it returned rows

                # LEGACY: This is the old crappy test -- easily fooled
                # if sql[0:6].lower() == 'select':

                if cursor.description:
                    outfile_base = f'{payload_num}.{n}{config("SQL_OUTPUT_SUFFIX")}'
                    outdir = os.path.join(tmpdir, *datadir)
                    outfile_full = os.path.join(outdir, outfile_base)
                    os.makedirs(outdir, exist_ok=True)

                    with open(outfile_full, 'w', newline='') as ofp:
                        # Customise the CSV writer
                        csv_writer = csv.writer(
                            ofp,
                            delimiter=parameters.get('delimiter', config('SQL_DELIMITER')),
                            doublequote=parameters.get(
                                'doublequote', config('SQL_DOUBLEQUOTE', str2bool)
                            ),
                            escapechar=parameters.get('escapechar', config('SQL_ESCAPECHAR')),
                            quotechar=parameters.get('quotechar', config('SQL_QUOTECHAR')),
                            quoting=quoting,
                            dialect=parameters.get('dialect', config('SQL_DIALECT')),
                        )

                        if parameters.get('header', False):
                            csv_writer.writerow(col[0] for col in cursor.description)

                        while True:
                            batch = cursor.fetchmany(batch_size)
                            if not batch:
                                break
                            csv_writer.writerows(batch)

                    # Copy to S3
                    s3file = '/'.join([s3tmp, *datadir, outfile_base])
                    s3bucket, s3key = s3_split(s3file)
                    s3_upload(
                        bucket=s3bucket,
                        key=s3key,
                        filename=outfile_full,
                        s3_client=aws_session.client('s3'),
                        kms_key=realm_info.get('s3_key'),
                    )
                    return_info['output'][f'{payload_num}'].append(s3file)

        if transaction:
            conn.commit()
            LOG.debug('Committed transaction')

    except Exception:
        if transaction:
            conn.rollback()
            LOG.debug('ROLLBACK')
        raise
    finally:
        conn.close()

    return return_info
