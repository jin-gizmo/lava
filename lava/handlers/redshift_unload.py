"""
Redshift unload handler.

Based on the pre-existing rsUnloader code.

"""

from __future__ import annotations

import logging
import re
from collections.abc import Iterable
from typing import Any

import boto3
import jinja2

from lava.config import LOGNAME
from lava.connection import get_aws_connection, get_pysql_connection
from lava.connection.core import make_application_name
from lava.lavacore import LavaError, jinja_render_vars
from lava.lib.aws import s3_check_bucket_security
from lava.lib.datetime import now_tz
from lava.lib.db import redshift_authorization, redshift_get_column_info2
from lava.lib.misc import dict_check

__author__ = 'Murray Andrews'

LOG = logging.getLogger(name=LOGNAME)

JOB_PARAMS_REQUIRED_FIELDS = {'conn_id', 'bucket', 'schema', 'relation', 'args'}

JOB_PARAMS_OPTIONAL_FIELDS = {
    'dateformat',
    'insecure',
    's3_conn_id',
    's3_iam_role',
    'vars',
    'prefix',
    'stop_on_fail',
    'start',
    'where',
    'key',  # Deprecated. Use prefix
}

REDSHIFT_UNLOAD_KEYS = {
    'ADDQUOTES',
    'ALLOWOVERWRITE',
    'BZIP2',
    'CLEANPATH',
    'CSV',
    'DELIMITER',
    'ENCRYPTED',
    'ESCAPE',
    'EXTENSION',
    'FIXEDWIDTH',
    'FORMAT',
    'GZIP',
    'HEADER',
    'JSON',
    'KMS_KEY_ID',
    'MANIFEST',
    'MAXFILESIZE',
    'NULL',
    'PARALLEL',
    'PARQUET',
    'PARTITION',
    'ROWGROUPSIZE',
    'ZSTD',
}

PARTITION_INDIRECT__RE = re.compile(
    r'BY\s+@\s*(?P<p_schema>[^.]+)\.(?P<p_relation>[^.]+)\s*$', re.I
)


# ------------------------------------------------------------------------------
def get_partition_cols(
    conn, p_schema: str, p_relation: str, u_schema: str, u_relation: str
) -> list[str]:
    """
    Retrieve the partition columns for a given relation from a metadata relation.

    The matadata relation is a (table or view) that contains information on
    partitions. The partition relation must contain the following columns:

        - schema_name (lower case)
        - rel_name (lower case)
        - partitions: A comma separated list of columns in the unload table.

    If this table contains multiple entries for the given unload relation then
    one is selected at random (so don't do that).

    :param conn:            A DBAPI 2.0 connection.
    :param p_schema:        The schema containing the partition info relation.
    :param p_relation:      The table or view containing the partition info.
    :param u_schema:        The schema containing the relation to be unloaded.
    :param u_relation:      The table or view to be unloaded.

    :return:                A  list of column names.

    :raise RuntimeError:    If the parition table cannit be accessed.
    :raise KeyError:        If there is no entry in the partition table for the
                            given unload relation.
    """

    cursor = conn.cursor()

    sql = (
        f'SELECT partitions FROM "{p_schema}"."{p_relation}" '
        'WHERE schema_name = %s AND rel_name = %s'
    )

    try:
        cursor.execute(sql, (u_schema.lower(), u_relation.lower()))
        partition_cols = cursor.fetchone()
    except Exception as e:
        raise RuntimeError(
            f'Cannot get partition info from {p_schema}.{p_relation}'
            f' for {u_schema}.{u_relation}: {e}'
        )

    if not partition_cols:
        raise KeyError(
            f'Cannot get partition info from {p_schema}.{p_relation}'
            f' for {u_schema}.{u_relation}: Not found'
        )

    return [c.strip() for c in partition_cols[0].split(',')]


# ------------------------------------------------------------------------------
def rs_unload_relation(
    cursor,
    schema: str,
    relation: str,
    bucket: str,
    prefix: str,
    authorization: str,
    unload_params: Iterable[str] = None,
    dateformat: str = None,
    where: str = None,
) -> str:
    """
    Unload a relation (table or view) from Redshift.

    :param cursor:          A DBAPI 2.0 cursor.
    :param schema:          Schema name.
    :param relation:        Relation (table or view) name.
    :param bucket:          Target S3 bucket name.
    :param prefix:          Target S3 prefix.
    :param authorization:   UNLOAD authorization parameters.
    :param unload_params:   An iterable of UNLOAD parameters.
    :param dateformat:      A Redshift datetime format string that will be
                            applied to DATE fields when unloading. The safest
                            value is YYYY-MM-DD. Default is None
    :param where:           An optional WHERE predicate for the unload query.

    :return:                The SQL used to do the unload without credentials.
    """

    # ----------------------------------------
    # Build the columns for the select statement.

    selector = '*'

    if dateformat:
        # We have to control date formatting -- see if any columns have dates
        columns = redshift_get_column_info2(cursor, schema, relation)

        for _, col_type in columns:
            # If we have any date columns at all need to name all columns in query
            if col_type == 'date':
                selector = ', '.join(
                    (
                        '"' + c[0] + '"'
                        if c[1] != 'date'
                        else fr'to_char("{c[0]}", \'{dateformat}\') AS "{c[0]}"'
                    )
                    for c in columns
                )
                break

    # ----------------------------------------
    # Setup the UNLOAD command -- no credentials yet so we can log
    where = 'WHERE ' + where.replace("'", "\\'") if where else ''
    unload_params = ' '.join(unload_params)
    unload_sql = f"""
                UNLOAD ('SELECT {selector} FROM "{schema}"."{relation}" {where}')
                TO 's3://{bucket}/{prefix}'
                {{authorization}}
                {unload_params};
            """
    # No credentials in the log please
    LOG.debug('Unload SQL: %s', unload_sql)

    secret_unload_sql = unload_sql.format(authorization=authorization)

    # ----------------------------------------
    # Show time

    cursor.execute(secret_unload_sql)

    return unload_sql


# ------------------------------------------------------------------------------
def rs_unload_option(
    opt: str, schema: str, relation: str, render_vars: dict[str, Any], conn
) -> str:
    """
    Apply transformations to a Redshift unload option.

    Specifics are option dependant.

    :param opt:         The option (e.g. PARALLEL ON, etc). See
                        https://docs.aws.amazon.com/redshift/latest/dg/r_UNLOAD.html
    :param schema:      Schema for the UNLOAD source relation.
    :param relation:    Table or view name for the UNLOAD.
    :param render_vars: A dictionary of Jinja2 render variables.
    :param conn:        An open database connection. This is used where data is
                        required from the unload source DB to manipulate UNLOAD
                        command options.

    :return:            The transformed option.
    """

    # Extract option keyword and any associated args
    try:
        opt_type, opt_args = opt.split(maxsplit=1)
    except ValueError:
        opt_type = opt
        opt_args = None

    opt_type = opt_type.upper()

    # ----------------------------------------
    if opt_type == 'PARTITION':
        if not opt_args:
            raise ValueError('PARTITION option requires argument(s)')
        m = PARTITION_INDIRECT__RE.match(opt_args)
        if m:
            # Get partition information from a control table in the UNLOAD source DB
            p_cols = ','.join(
                [
                    f'"{c}"'
                    for c in get_partition_cols(
                        conn, m.group('p_schema'), m.group('p_relation'), schema, relation
                    )
                ]
            )
            opt = f'PARTITION BY ({p_cols})'
        else:
            # Otherwise just render the PARTITION args
            opt = jinja2.Template(opt).render(**render_vars)

    LOG.debug(f'Redshift unload option for {schema}.{relation}: {opt}')

    # ----------------------------------------
    return opt


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
    Run a Redshift UNLOAD.

    Allowed job parameters are (* means optional):

    - conn_id
        A connectiion ID for the target DB.

    - s3_conn_id*
        A connection ID for S3.

    - s3_iam_role*
        Alternative to s3_conn_id. At least one of these must be provided.

    - bucket
        Target bucket.

    - prefix | key
        Target S3 prefix (key is legacy and will be removed in a future
        release).

    - schema
        Source schema.

    - relation
        Source relation or a list of source relations.

    - where*
        An optional WHERE predicate for the unload query. Do not include the
        WHERE keyword.

    - args
        A list of parameters for the UNLOAD command. All of the Redshift
        supported parameters except for the authorization parameters are
        supported.

    - dateformat*
        A Redshift datetime format string that will be applied to DATE fields
        when unloading. The safest value is YYYY-MM-DD.

    - insecure*
        Disable bucket security checks. Default is false. Seriously, don't
        set this to true unless you really know what you're doing.

    - stop_on_fail*
        If true, stop when any unload fails otherwise keep moving through the
        unload list. Default is true.

    - start*
        Name of the relation to start with in a sequence of relations.

    - vars*
        A map of variables injected when jinja rendering is done.

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

    parameters = job_spec['parameters']

    # ----------------------------------------
    # Validate job parameters.

    try:
        dict_check(
            parameters, required=JOB_PARAMS_REQUIRED_FIELDS, optional=JOB_PARAMS_OPTIONAL_FIELDS
        )
    except ValueError as e:
        raise LavaError(f'Bad job parameters: {e}')

    # prefix or key (legacy) required
    prefix = parameters.get('prefix', parameters.get('key'))
    if not prefix:
        raise LavaError('Bad job parameters: prefix is required')

    if 'key' in parameters:
        LOG.warning(
            '%s: Deprecation warning: key parameter should be replaced by prefix',
            job_spec['job_id'],
            extra={'event_type': 'job', 'job_id': job_spec['job_id'], 'run_id': job_spec['run_id']},
        )

    unload_keywords = {ulp.split()[0].upper() for ulp in parameters['args']}

    bad_args = unload_keywords - REDSHIFT_UNLOAD_KEYS
    if bad_args:
        raise LavaError('Invalid UNLOAD arguments: {}'.format(', '.join(bad_args)))

    stop_on_fail = parameters.get('stop_on_fail', True)
    s3bucket = parameters['bucket']

    try:
        start = parameters['start']
    except KeyError:
        start = None

    # ----------------------------------------
    # Get S3 connection details
    try:
        s3_iam_role = parameters['s3_iam_role']
        s3_access_keys = {}
    except KeyError:
        s3_iam_role = None
        try:
            s3_conn_id = parameters['s3_conn_id']
        except KeyError:
            raise LavaError('At least one of s3_iam_role and s3_conn_id is required')
        s3_access_keys = get_aws_connection(s3_conn_id, job_spec['realm'], aws_session=aws_session)

    # ----------------------------------------
    # Check bucket security
    if not parameters.get('insecure', False):
        LOG.debug(f'Checking bucket security on {s3bucket}')
        try:
            s3_check_bucket_security(s3bucket, aws_session=aws_session)
        except Exception as e:
            raise LavaError(f'Bucket {s3bucket} is insecure: {e}')
    else:
        LOG.warning(
            f'{job_spec["realm"]}@{job_spec["job_id"]}: Possible insecure redshift_unload',
            extra={'event_type': 'job', 'job_id': job_spec['job_id'], 'run_id': job_spec['run_id']},
        )

    # ----------------------------------------
    # Get a connection to the target DB.
    conn_id = parameters['conn_id']
    conn = get_pysql_connection(
        conn_id,
        job_spec['realm'],
        aws_session=aws_session,
        application_name=make_application_name(
            conn_id=conn_id, realm=job_spec['realm'], job_id=job_spec['job_id']
        ),
    )

    # ----------------------------------------
    schema = parameters['schema']
    relation = parameters['relation']
    relations = [relation] if isinstance(relation, str) else relation
    where_p = parameters.get('where')  # type: str

    return_info = {'exit_status': 0, 'unloads': []}

    # ----------------------------------------
    failures = []
    started = False
    try:
        with conn.cursor() as cursor:
            for relation in relations:
                render_vars = jinja_render_vars(
                    job_spec,
                    realm_info,
                    schema=schema,
                    relation=relation,
                    vars=parameters.get('vars', {}),
                )

                # Check if we are skipping relations looking for a starting point
                if start and not started and relation.lower() != start:
                    continue

                started = True
                ts_unload_start = now_tz()
                where = jinja2.Template(where_p).render(**render_vars) if where_p else where_p

                task_info = {
                    'schema': schema,
                    'relation': relation,
                    'bucket': s3bucket,
                    'prefix': prefix,
                    'ts_start': ts_unload_start.isoformat(),
                }

                # Construct the S3 target location
                try:
                    task_info['prefix'] = jinja2.Template(prefix).render(**render_vars)
                    # We do not permit single quote in a key name
                    if "'" in task_info['prefix']:
                        raise ValueError('Single quote not allowed in S3 prefix')
                except Exception as e:
                    raise LavaError(f'Bad prefix parameter: {e}')

                try:
                    task_info['sql'] = rs_unload_relation(
                        cursor=cursor,
                        schema=schema,
                        relation=relation,
                        bucket=s3bucket,
                        prefix=task_info['prefix'],
                        authorization=redshift_authorization(
                            s3_iam_role=s3_iam_role, **s3_access_keys
                        ),
                        # Preprocess our unload options.
                        unload_params=(
                            rs_unload_option(opt, schema, relation, render_vars, conn)
                            for opt in parameters['args']
                        ),
                        dateformat=parameters.get('dateformat'),
                        where=where,
                    ).strip(' \n')
                except Exception as e:
                    task_info['status'] = 'failed'
                    task_info['error'] = str(e)
                    return_info['unloads'].append(task_info)
                    if stop_on_fail:
                        raise
                    LOG.warning(
                        f'Unload of {schema}.{relation} failed: {e}',
                        extra={
                            'event_type': 'job',
                            'job_id': job_spec['job_id'],
                            'run_id': job_spec['run_id'],
                        },
                    )
                    failures.append(relation)
                    continue

                ts_unload_finish = now_tz()
                task_info['ts_finish'] = ts_unload_finish.isoformat()
                task_info['duration'] = round((ts_unload_finish - ts_unload_start).total_seconds())
                task_info['status'] = 'complete'

                return_info['unloads'].append(task_info)

    except Exception as e:
        return_info['exit_status'] = 1
        return_info['error'] = str(e)
        raise LavaError(f'Unload failed: {e}', data=return_info)
    finally:
        if conn:
            conn.close()

    if failures:
        return_info['failures'] = failures
        raise LavaError(f'{len(failures)} unloads failed', data=return_info)

    if not return_info['unloads']:
        raise LavaError('No unloads were attempted', data={'start': start} if start else None)

    return return_info
