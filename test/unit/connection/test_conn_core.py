"""Test connection core components."""

import pytest  # noqa

import lava.connection
import lava.connection.core
from lava.lib.smb import LavaSMBConnection, SMBConnectionError
from test.const import REALM

SMB_DRIVERS = ['pysmb', 'smbprotocol']
SMB_CONNECTORS = ['smb/lava-test-smb/pysmb', 'smb/lava-test-smb/smbprotocol']
SQL_CONNECTORS = ['db/psql/local', 'db/mysql/local']


# ------------------------------------------------------------------------------
@pytest.mark.parametrize(
    'application_name,expected',
    [
        ('name', 'name'),
        ('na"me', 'name'),
        ("na'me", 'name'),
    ],
)
def test_clean_application_name(application_name, expected):
    assert lava.connection.core.clean_application_name(application_name) == expected


# ------------------------------------------------------------------------------
@pytest.mark.parametrize(
    'realm,job_id,conn_id,expected',
    [
        (REALM, 'my_job', 'my_conn', f'lv-{REALM}-my_job'),
        (REALM, None, 'my_conn', None),  # no job ID ==> no app name
        (None, 'my_job', 'my_conn', 'lv-xyzzy-my_job'),
    ],
)
def test_make_application_name(realm: str, job_id: str, conn_id: str, expected: str, monkeypatch):
    if not realm:
        monkeypatch.setenv('LAVA_REALM', 'xyzzy')

    assert (
        lava.connection.core.make_application_name(job_id=job_id, realm=realm, conn_id=conn_id)
        == expected
    )


# ------------------------------------------------------------------------------
def test_get_connection_spec_no_such_conn(tc):
    with pytest.raises(Exception, match='No such connection'):
        lava.connection.get_connection_spec(conn_id='no-such-conn', realm=tc.realm)


# ------------------------------------------------------------------------------
def test_get_connection_spec_bad_conn(tc):
    with pytest.raises(Exception, match='Bad connection record'):
        lava.connection.get_connection_spec(conn_id=f'{tc.prefix.conn}/bad_conn', realm=tc.realm)


# ------------------------------------------------------------------------------
@pytest.mark.local
@pytest.mark.parametrize('name', SQL_CONNECTORS)
def test_get_pysql_connection_ok(name: str, tc):
    """Test getting DBAPI 2 connections."""

    conn = lava.connection.get_pysql_connection(f'{tc.prefix.conn}/{name}', realm=tc.realm)
    assert hasattr(conn, 'cursor')


# ------------------------------------------------------------------------------
@pytest.mark.local
@pytest.mark.parametrize('driver', SMB_DRIVERS)
def test_get_smb_conn_ok(driver: str, tc, smb_conn_prefix):
    """Test getting SMB connection."""

    conn = lava.connection.get_smb_connection(f'{smb_conn_prefix}/{driver}', realm=tc.realm)
    assert isinstance(conn, LavaSMBConnection)
    assert conn.connected

    conn.close()


# ------------------------------------------------------------------------------
@pytest.mark.local
@pytest.mark.parametrize(
    'driver',
    [
        'pysmb',
        pytest.param(
            'smbprotocol',
            marks=pytest.mark.xfail(
                reason='SMBprotocol handler raises SMBOperationError not SMBConnectionError'
            ),
        ),
    ],
)
def test_get_smb_conn_auth_fail(driver: str, tc, smb_conn_prefix):
    conn_spec = lava.connection.core.get_smb_conn_spec(
        conn_id=f'{smb_conn_prefix}/{driver}', realm=tc.realm
    )

    conn_spec['password'] = 'bad pass'

    # TODO: The SMBprotocol handler raises an SMBOperationError here. It shouldn't.
    with pytest.raises(SMBConnectionError):
        lava.connection.core._get_smb_connection(conn_spec)


# ------------------------------------------------------------------------------
@pytest.mark.local
@pytest.mark.parametrize(
    'driver',
    [
        pytest.param(
            'pysmb',
            marks=pytest.mark.xfail(
                reason='pysmb raises ConnectionRefusedError -- should be SMBConnectionError'
            ),
        ),
        'smbprotocol',
    ],
)
def test_get_smb_conn_fail(driver: str, tc, smb_conn_prefix):
    conn_spec = lava.connection.core.get_smb_conn_spec(
        conn_id=f'{smb_conn_prefix}/{driver}', realm=tc.realm
    )

    conn_spec['port'] = 9999  # Should be an unused port.

    # TODO: pysmb handler raises ConnectionRefusedError -- should be SMBConnectionError
    with pytest.raises(SMBConnectionError):
        lava.connection.core._get_smb_connection(conn_spec)
