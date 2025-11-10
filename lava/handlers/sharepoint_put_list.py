"""Put a list into a SharePoint site."""

from __future__ import annotations

import csv
import logging
import os.path
from typing import Any

import boto3
import jinja2

from lava.config import LOGNAME, config
from lava.connection import get_sharepoint_connection
from lava.lavacore import LavaError, jinja_render_vars
from lava.lib.aws import s3_download, s3_split
from lava.lib.misc import dict_check, str2bool

__author__ = 'Murray Andrews'

LOG = logging.getLogger(name=LOGNAME)

JOB_PARAMS_REQUIRED_FIELDS = {'conn_id', 'list', 'file'}
JOB_PARAMS_OPTIONAL_FIELDS = {
    'jinja',
    'mode',
    'vars',
    'basedir',
    'error_missing',
    'delimiter',
    'doublequote',
    'escapechar',
    'quotechar',
    'quoting',
    'data_columns',
}


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
    Put a list into a SharePoint site.

    Allowed job parameters are (* means optional):

    - conn_id
        A connection ID for the target SharePoint site.

    - list
        Name of the list. This will be jinja rendered.

    - file
        Source file. If it starts with `s3://` it is assumed to be an object in
        S3, otherwise a local file. If local and not an absolute path, it will
        be treated as relative to the basedir parameter. This will be jinja
        rendered. This will be jinja rendered.

    - basedir
        If the source file is specified as a relative filename, it will be
        treated as relative to the specified directory. Defaults to the lava
        temporary directory for the job.

    - mode*
        Either `append`, `delete`, `replace` or `update`. Default is `append`.

    - error_missing
        If True and there are columns in the source file but not in the
        SharePoint list, raise an error.

    - jinja*
        An optional boolean indicating whether Jinja rendering is enabled for
        the target path and description. Default True.

    - vars*
        An optional dictionary of variables to use when Jinja rendering.

    - data_columns
        If specified, then only columns listed there are provided (additionally
        system_columns are added if given). This is a comma separated list of
        column names.

    Optional CSV formatting parameters:

    - delimiter*
        Field delimiter. Default '|'

    - doublequote*
        As for csv.reader. Default False.

    - escapechar*
        As for csv.reader. Default None.

    - quotechar*
        As for csv.reader. Default '"'.

    - quoting*
        As for csv.reader ``QUOTE_`` parameters (without the ``QUOTE_`` prefix).
        Default "minimal" (QUOTE_MINIMAL).

    The payload is ignored.

    :param job_spec:        The job spec from the DynamoDB database.
    :param realm_info:      Realm specific parameters.
    :param tmpdir:          A local temporary directory.
    :param s3tmp:           A prefix in S3 where temporary assets can be created
                            and left for others to pick up for limited time.
    :param dev_mode:        If True, emit stdout / stderr locally instead of
                            copying to S3. Default False.
    :param aws_session:     A boto3 Session()

    :return:                A dictionary of parameters that are available to
                            on-success, on-error, on-retry handlers.

    """

    parameters = job_spec.get('parameters', {})
    try:
        dict_check(
            parameters, required=JOB_PARAMS_REQUIRED_FIELDS, optional=JOB_PARAMS_OPTIONAL_FIELDS
        )
    except ValueError as e:
        raise LavaError(f'Bad job parameters: {e}')

    quoting_style = parameters.get('quoting', config('SP_LIST_QUOTING')).upper()

    try:
        quoting = getattr(csv, 'QUOTE_' + quoting_style)
    except AttributeError:
        raise LavaError(f'Bad quoting atyle: {quoting_style}')

    basedir = parameters.get('basedir', tmpdir)

    # ----------------------------------------
    # Get connection for the target SharePoint site

    conn_id = parameters['conn_id']
    conn = get_sharepoint_connection(conn_id, job_spec['realm'], aws_session=aws_session)

    # ----------------------------------------
    # Jinja rendering

    list_name = parameters['list']
    src_file = parameters['file']  # type: str

    if parameters.get('jinja', True):
        job_vars = parameters.get('vars', {})
        if not isinstance(job_vars, dict):
            raise LavaError('vars must be a map/dict')
        render_vars = jinja_render_vars(job_spec, realm_info, vars=job_vars)

        list_name = jinja2.Template(list_name).render(**render_vars)
        src_file = jinja2.Template(src_file).render(**render_vars)

    # ----------------------------------------
    # Get the source file

    if src_file.startswith('s3://'):
        if not aws_session:
            aws_session = boto3.Session()
        src_bucket, src_key = s3_split(src_file)
        src_local = os.path.join(tmpdir, os.path.basename(src_file))
        s3_download(src_bucket, src_key, src_local, aws_session.client('s3'))
    elif os.path.isabs(src_file):
        src_local = src_file
    else:
        src_local = os.path.join(basedir, src_file)

    # ----------------------------------------
    # Copy to SharePoint

    LOG.debug(f'Uploading {src_local} to list {list_name}')

    try:
        n = conn.put_list(
            list_name,
            src_local,
            mode=parameters.get('mode', 'append'),
            data_columns=parameters.get('data_columns'),
            error_missing=parameters.get('error_missing', False),
            # CSV formatting args
            delimiter=parameters.get('delimiter', config('SP_LIST_DELIMITER')),
            doublequote=parameters.get('doublequote', config('SP_LIST_DOUBLEQUOTE', str2bool)),
            escapechar=parameters.get('escapechar', config('SP_LIST_ESCAPECHAR')),
            quotechar=parameters.get('quotechar', config('SP_LIST_QUOTECHAR')),
            quoting=quoting,
        )
    finally:
        conn.close()

    # ----------------------------------------
    return {
        'exit_status': 0,
        'row_count': n,
        'source': src_file,
        'destination': list_name,
    }
