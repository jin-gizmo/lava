"""Lava specific modules."""

from os import environ

from .lavacore import (
    LavaError as LavaError,
    dispatch as dispatch,
    get_job_spec as get_job_spec,
    get_realm_info as get_realm_info,
    scan_jobs as scan_jobs,
    scan_realms as scan_realms,
)
from .version import __version__, __version_name__, __version_num__  # noqa: F401

__author__ = 'Murray Andrews'

# Handle update to botocore handling of SQS queue endpoints.
# See https://github.com/boto/botocore/issues/2705
environ['BOTO_DISABLE_COMMONNAME'] = 'true'

__all__ = [
    'LavaError',
    '__version__',
    '__version_name__',
    '__version_num__',
    'dispatch',
    'get_job_spec',
    'get_realm_info',
    'scan_jobs',
    'scan_realms',
]
