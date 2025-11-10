"""
Common lava specific functions.

These can't be in lava or lavacore to avoid circular imports.
"""

__author__ = 'Murray Andrews'

from threading import RLock

import boto3
from cachetools import TTLCache, cached

from lava.config import LOG, config
from lava.lib.aws import ssm_get_param
from lava.lib.datetime import duration_to_seconds

PARAM_CACHE_TTL = config('PARAM_CACHE_TTL', duration_to_seconds)
PARAM_CACHE_SIZE = config('PARAM_CACHE_SIZE', int)
_PARAM_CACHE = (
    TTLCache(maxsize=PARAM_CACHE_SIZE, ttl=PARAM_CACHE_TTL) if PARAM_CACHE_TTL > 0 else {}
)


# ------------------------------------------------------------------------------
@cached(_PARAM_CACHE, lock=RLock(), key=lambda name, aws_session: name)
def get_lava_param(name: str, aws_session: boto3.Session = None) -> str:
    """
    Read a secure parameter from AWS SSM service.

    Parameters are cached for a limited period of time.

    !!! warning
        The way in which the `cached()` decorator is implemented is a bit
        debatable with respect to the lock mechanism. It does not include the
        function invocation itself inside the lock (`get_lava_param()` in this
        case). Only the cache management is inside the lock. That means it does
        not prevent multiple threads from executing the parameter fetch at the
        same time. The upside of this approach is that it prevents one parameter
        fetch from blocking another, even when they are for different
        parameters. You pay your money and you take your chances.

    :param name:        Valid SSM parameter name
    :param aws_session: A boto3 Session. If None a default is created.

    :return:            The parameter value.

    :raise Exception:   If the parameter doesn't exist or cannot be accessed.
    """

    LOG.debug('Fetching SSM parameter: %s', name)
    return ssm_get_param(name, aws_session=aws_session)
