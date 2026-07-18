"""
Shared SSL utilities for the lava database connectivity layer.

Provides a uniform approach to SSL configuration across DBAPI 2.0 drivers,
implementing a three-level security model:

|Level|  ssl_mode   | Description                                           |
|:---:|-------------|-------------------------------------------------------|
|  0  |             | No SSL (default)                                      |
|  1  | require     | SSL active, no cert validation, no hostname checking. |
|  2  | verify-ca   | SSL active, cert validated, no hostname checking.     |
|  3  | verify-full | SSL active, cert validated, hostname checked.         |

!!! note
    For backward compatibility, `ssl=True` is treated as being equivalent to
    `ssl_mode='require'`. Use the `ssl_mode` parameter in preference.

"""

from __future__ import annotations

import ssl

import smart_open

# The values here are a tuple (check_hostname, SSLContext.verify_mode)
SSL_MODES = {
    'require': (False, ssl.CERT_NONE),
    'verify-ca': (False, ssl.CERT_REQUIRED),
    'verify-full': (True, ssl.CERT_REQUIRED),
}


# ------------------------------------------------------------------------------
# noinspection PyUnusedLocal
def resolve_ssl_mode(
    ssl: bool = None,  # noqa A002  -- shadows builtin intentionally
    ssl_mode: str = None,
    **kwargs,
) -> str | None:
    """
    Resolve the effective SSL mode from connection specification values.

    :param ssl:       Legacy boolean SSL flag from the connection specification.
    :param ssl_mode:  SSL mode string: 'require', 'verify-ca', or 'verify-full'.
    :param kwargs:    Remaining connection spec fields (ignored).
    :return:          Normalised ssl_mode string, or None for no SSL.
    :raise ValueError: If ssl_mode is not a recognised value.
    """

    if ssl_mode is not None:
        if ssl_mode not in SSL_MODES:
            raise ValueError(f'Bad ssl_mode: {ssl_mode}')
        return ssl_mode

    return 'require' if ssl else None


# ------------------------------------------------------------------------------
def build_ssl_context(ssl_mode: str, ssl_ca_file: str = None) -> ssl.SSLContext:
    """
    Build a configured SSLContext for the given SSL mode.

    Uses ssl.create_default_context() as the base, which loads the system
    trust store and enforces modern cipher suites and TLS 1.2+.

    :param ssl_mode:    Normalised SSL mode string from resolve_ssl_mode().
                        Must be one of 'require', 'verify-ca', 'verify-full'.
    :param ssl_ca_file: Path or URI to a PEM-format CA certificate file.
                        Supports local paths and any URI scheme handled by
                        smart_open (e.g. s3://, http://). If None, the system
                        trust store is used (only meaningful for verify-ca /
                        verify-full).
    :return:           A configured ssl.SSLContext.
    :raise ValueError: If ssl_mode is not a recognised value.
    """

    ctx = ssl.create_default_context()

    try:
        check_hostname, verify_mode = SSL_MODES[ssl_mode]
    except KeyError:
        raise ValueError(f'Bad ssl_mode {ssl_mode}')

    # Important to set check_hostname first if ctx.verify_mode is CERT_NONE.
    ctx.check_hostname = check_hostname
    ctx.verify_mode = verify_mode

    if ssl_ca_file:
        with smart_open.open(ssl_ca_file, 'r') as f:
            ca_data = f.read()
        ctx.load_verify_locations(cadata=ca_data)

    return ctx
