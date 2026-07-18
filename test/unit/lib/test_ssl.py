"""Test cases for lava.libssl"""

import pytest  # noqa

from lava.lib.ssl import *
import ssl


def cert_subject_dict(cert):
    """Get the subject dict from an X.509 certificate."""
    return dict(pair for rdn in cert['subject'] for pair in rdn)


# ------------------------------------------------------------------------------
@pytest.mark.parametrize(
    'ssl, ssl_mode, expected',
    [
        (False, None, None),
        (False, 'require', 'require'),
        (True, 'require', 'require'),
        (True, 'verify-full', 'verify-full'),
        (True, None, 'require'),
    ],
)
def test_resolve_ssl_mode_ok(ssl, ssl_mode, expected):  # noqa A002
    assert resolve_ssl_mode(ssl, ssl_mode) == expected


def test_resolve_ssl_mode_bad_mode():
    with pytest.raises(ValueError, match='Bad ssl_mode'):
        resolve_ssl_mode(False, 'bad-mode')


# ------------------------------------------------------------------------------
@pytest.mark.parametrize(
    'ssl_mode, expected_check_hostname, expected_verify_mode',
    [
        ('require', False, ssl.CERT_NONE),
        ('verify-ca', False, ssl.CERT_REQUIRED),
        ('verify-full', True, ssl.CERT_REQUIRED),
    ],
)
def test_build_ssl_context_ok(ssl_mode, expected_check_hostname, expected_verify_mode, dirs):

    cert_file = str(dirs.services / 'postgres/postgres/server.crt')

    ctx = build_ssl_context(ssl_mode, cert_file)

    assert ctx.check_hostname == expected_check_hostname
    assert ctx.verify_mode == expected_verify_mode

    cert_cns = [cert_subject_dict(cert).get('commonName') for cert in ctx.get_ca_certs()]
    assert 'lava-test-postgres' in cert_cns


def test_build_ssl_context_bad_mode():
    with pytest.raises(ValueError, match='Bad ssl_mode'):
        build_ssl_context('bad-mode')
