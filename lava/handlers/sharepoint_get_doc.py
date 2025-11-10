"""Get a document from a document library in a SharePoint site."""

from __future__ import annotations

import logging
import os.path
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

JOB_PARAMS_REQUIRED_FIELDS = {'conn_id', 'library', 'path', 'file'}
JOB_PARAMS_OPTIONAL_FIELDS = {'basedir', 'jinja', 'kms_key_id', 'vars'}


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

    - file
        Target file. If it starts with `s3://` it is assumed to be an object in
        S3, otherwise a local file. If local and not an absolute path, it will
        be treated as relative to the basedir parameter. This will be jinja
        rendered. This will be jinja rendered.

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
    dst_file = parameters['file']  # type: str

    if parameters.get('jinja', True):
        job_vars = parameters.get('vars', {})
        if not isinstance(job_vars, dict):
            raise LavaError('vars must be a map/dict')
        render_vars = jinja_render_vars(job_spec, realm_info, vars=job_vars)

        path = jinja2.Template(path).render(**render_vars)
        library = jinja2.Template(library).render(**render_vars)
        dst_file = jinja2.Template(dst_file).render(**render_vars)

    # ----------------------------------------
    # Prepare destination file

    if dst_file.startswith('s3://'):
        dst_bucket, dst_key = s3_split(dst_file)
        dst_local = os.path.join(tmpdir, os.path.basename(dst_file))
    elif os.path.isabs(dst_file):
        # Local absolute path
        dst_bucket, dst_key = None, None
        dst_local = dst_file
    else:
        # Local relative path.
        dst_bucket, dst_key = None, None
        dst_local = os.path.join(basedir, dst_file)

    # ----------------------------------------
    # Get doc from SharePoint

    LOG.debug(f'Downloading {path} to {dst_local}')
    try:
        doc_title = conn.get_doc(library, path, dst_local)
    finally:
        conn.close()

    # ----------------------------------------
    # Push it back to S3

    if dst_bucket:
        if not aws_session:
            aws_session = boto3.Session()

        LOG.debug(f'Uploading {dst_local} to s3://{dst_bucket}/{dst_key}')
        s3_upload(
            bucket=dst_bucket,
            key=dst_key,
            filename=dst_local,
            kms_key=parameters.get('kms_key_id'),
            s3_client=aws_session.client('s3'),
        )

    # ----------------------------------------
    return {
        'exit_status': 0,
        'title': doc_title,
        'source': path,
        'destination': dst_file,
        'library': library,
    }
