"""Get a document from a document library in a SharePoint site."""

from __future__ import annotations

import logging
import os.path
from contextlib import suppress
from typing import Any

import boto3
import jinja2

from lava.config import LOGNAME
from lava.connection import get_sharepoint_connection
from lava.lavacore import LavaError, jinja_render_vars
from lava.lib.aws import s3_split, s3_upload
from lava.lib.misc import dict_check

__author__ = 'Murray Andrews'

LOG = logging.getLogger(name=LOGNAME)

JOB_PARAMS_REQUIRED_FIELDS = {'conn_id', 'library', 'path', 'outpath'}
JOB_PARAMS_OPTIONAL_FIELDS = {'glob', 'basedir', 'jinja', 'kms_key_id', 'vars'}


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
    Get a document from a document library in a SharePoint site.

    Allowed job parameters are (* means optional):

    - conn_id
        A connection ID for the source SharePoint site.

    - library
        Source SharePoint library name. This will be jinja rendered.

    - path
        Source path within the library. This will be jinja rendered.

    - outpath
        Target path. If it starts with `s3://` it is assumed to be an S3 bucket
        and base key prefix name, otherwise a local file. If s3 type then path
        must end in `/`  to use CommonPrefixes s3 key semantics (like a folder)
        If local and not an absolute path, it will be treated as relative to
        the basedir parameter. This will be jinja rendered.

    - glob*
        Download files that match this glob. Match only files present in the
        path and not subfolders. Matching is case-insentive. This will be
        jinja rendered.

    - basedir
        If the target file is specified as a relative filename, it will be
        treated as relative to the specified directory. Defaults to the lava
        temporary directory for the job.

    - kms_key_id*
        AWS KMS key to use for uploading data to S3.

    - jinja*
        An optional boolean indicating whether Jinja rendering is enabled for
        the target path. Default True.

    - vars*
        An optional dictionary of variables to use when Jinja rendering.

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

    basedir = parameters.get('basedir', tmpdir)

    # ----------------------------------------
    # Get connection for the target SharePoint site

    conn_id = parameters['conn_id']
    conn = get_sharepoint_connection(conn_id, job_spec['realm'], aws_session=aws_session)

    # ----------------------------------------
    # Jinja rendering

    path = parameters['path']
    library = parameters['library']
    dst_path = parameters['outpath']  # type: str
    glob = parameters.get('glob')

    if parameters.get('jinja', True):
        job_vars = parameters.get('vars', {})
        if not isinstance(job_vars, dict):
            raise LavaError('vars must be a map/dict')
        render_vars = jinja_render_vars(job_spec, realm_info, vars=job_vars)

        path = jinja2.Template(path).render(**render_vars)
        library = jinja2.Template(library).render(**render_vars)
        dst_path = jinja2.Template(dst_path).render(**render_vars)
        if glob:
            glob = jinja2.Template(glob).render(**render_vars)

    # ----------------------------------------
    # Prepare destination file

    if dst_path.startswith('s3://'):
        dst_bucket, dst_key = s3_split(dst_path)
        if dst_path.endswith('/'):
            dst_key += '/'
            dst_local = os.path.join(tmpdir, os.path.basename(dst_path.strip('/')))
        else:
            dst_local = os.path.join(tmpdir, os.path.basename(dst_path))
    elif os.path.isabs(dst_path):
        # Local absolute path
        dst_bucket, dst_key = None, None
        dst_local = dst_path
    else:
        # Local relative path.
        dst_bucket, dst_key = None, None
        dst_local = os.path.join(basedir, dst_path)

    with suppress(FileExistsError):
        os.mkdir(dst_local)

    # ----------------------------------------
    # Get doc from SharePoint

    if glob:
        LOG.debug(f'Downloading files {path}/{glob} to {dst_local}')
    else:
        LOG.debug(f'Downloading all files in {path} to {dst_local}')
    try:
        file_list = conn.get_multi_doc(library, path, dst_local, glob)
    finally:
        conn.close()

    # ----------------------------------------
    # Push files to S3

    if dst_bucket:
        if not aws_session:
            aws_session = boto3.Session()

        for filename in file_list:
            LOG.debug(f'Uploading file in {filename} to s3://{dst_bucket}/{dst_key}{filename}')
            s3_upload(
                bucket=dst_bucket,
                key=f'{dst_key}{filename}',
                filename=os.path.join(dst_local, filename),
                kms_key=parameters.get('kms_key_id'),
                s3_client=aws_session.client('s3'),
            )

    # ----------------------------------------
    return {
        'exit_status': 0,
        'files': file_list,
        'source': path,
        'destination': dst_path,
        'library': library,
    }
