"""Test the SMB utility functions."""

from uuid import uuid4

import lava.connection
import pytest
from .conftest import SMB_SHARED_DIR
from lava.lib.smb import *

SMB_SERVICE_NAME = 'lavatest'

SMB_CONNECTORS = [
    'lava-test-smb/pysmb',
    'lava-test-smb/smbprotocol',
]


# ------------------------------------------------------------------------------
# @pytest.mark.usefixtures('dirs', 'request')
class SMBTestFilePair:
    """
    Represent a file name into its local and remote equivalents.

    These both refer to the same file on the local host because of the way the
    volume mapping on the SMB container works.

    :param name:    The object name. If not specified, a UUID based name in
                    in the `lava` directory is generated.
    :param suffix:  If specified, append it the file name.
    """

    def __init__(self, name: str | None = None, suffix: str | None = None):
        if not name:
            name = f'lava/{uuid4()}'
        if suffix:
            name += suffix
        self.local = SMB_SHARED_DIR / name
        # # self.local = self.dirs.smb_share / name
        # self.local = self.smb_share(request) / name
        self.remote = name


# ------------------------------------------------------------------------------
@pytest.mark.local
@pytest.mark.parametrize('name', SMB_CONNECTORS)
def test_list_path(name: str, tc):
    with lava.connection.get_smb_connection(f'{tc.prefix.conn}/smb/{name}', realm=tc.realm) as conn:
        result = conn.list_path(SMB_SERVICE_NAME, 'lava')
        hello_file = None
        for f in result:
            if f.filename == 'hello.txt':
                hello_file = f
        assert hello_file


# ------------------------------------------------------------------------------
@pytest.mark.local
@pytest.mark.parametrize('name', SMB_CONNECTORS)
def test_search_path(name: str, tc):
    with lava.connection.get_smb_connection(f'{tc.prefix.conn}/smb/{name}', realm=tc.realm) as conn:
        result = conn.list_path(SMB_SERVICE_NAME, 'lava', pattern='*.txt')
        for f in result:
            if f.filename == 'hello.txt':
                break
        else:
            assert False, 'Failed to find hello.txt'


# ------------------------------------------------------------------------------
@pytest.mark.local
@pytest.mark.parametrize('name', ['lava-test-smb/smbprotocol'])
def test_search_with_pattern(name: str, tc):
    """Test SMB protocol _search_with_pattern()."""

    dir1 = SMBTestFilePair(suffix='.d')
    with lava.connection.get_smb_connection(f'{tc.prefix.conn}/smb/{name}', realm=tc.realm) as conn:
        assert isinstance(conn, SMBProtocolConnection)
        conn.create_directory(SMB_SERVICE_NAME, dir1.remote)
        assert dir1.local.is_dir()


# ------------------------------------------------------------------------------
@pytest.mark.local
@pytest.mark.parametrize('name', SMB_CONNECTORS)
def test_smbfile_cls(name: str, tc, smb_hello_file):
    """Test aspects of SMBfile class."""

    with lava.connection.get_smb_connection(f'{tc.prefix.conn}/smb/{name}', realm=tc.realm) as conn:
        hello_file = conn.get_attributes(SMB_SERVICE_NAME, 'lava/hello.txt')
        assert hello_file.filename == 'hello.txt'
        assert hello_file.file_size == len(smb_hello_file)
        assert not hello_file.is_directory
        assert not hello_file.is_read_only
        assert hello_file.is_normal, f'Expected file {hello_file.filename} to be "NORMAL"'
        assert (
            'NORMAL' in hello_file.get_readable_attributes()
        ), f'Expected file {hello_file.filename} attributes to include "NORMAL"'


# ------------------------------------------------------------------------------
@pytest.mark.local
@pytest.mark.parametrize(
    'name,match',
    [
        ('lava-test-smb/pysmb', 'Unable to open remote file object'),
        ('lava-test-smb/smbprotocol', 'The file does not exist'),
    ],
)
def test_get_file_fail(name: str, match: str, tc, smb_hello_file):
    with lava.connection.get_smb_connection(f'{tc.prefix.conn}/smb/{name}', realm=tc.realm) as conn:
        with pytest.raises(SMBOperationError, match=match):
            conn.get_attributes(SMB_SERVICE_NAME, 'lava/nosuchfile')


# ------------------------------------------------------------------------------
@pytest.mark.local
@pytest.mark.parametrize('name', SMB_CONNECTORS)
def test_directory_manipulation(name: str, tc, smb_shared_dir):
    dir1 = SMBTestFilePair()
    dir2 = SMBTestFilePair()

    with lava.connection.get_smb_connection(f'{tc.prefix.conn}/smb/{name}', realm=tc.realm) as conn:
        conn.create_directory(SMB_SERVICE_NAME, dir1.remote)
        # Check dir is visible through the shared vol
        assert dir1.local.is_dir()

        # Rename it
        conn.rename(SMB_SERVICE_NAME, dir1.remote, dir2.remote)
        assert not dir1.local.exists()
        assert dir2.local.is_dir()

        # Remove it
        conn.delete_directory(SMB_SERVICE_NAME, dir2.remote)
        assert not dir2.local.exists()


# ------------------------------------------------------------------------------
@pytest.mark.local
@pytest.mark.parametrize('name', SMB_CONNECTORS)
def test_file_manipulation(name: str, tc, smb_hello_file, smb_shared_dir, tmp_path):
    local_file1 = tmp_path / str(uuid4())
    file2 = SMBTestFilePair()
    file3 = SMBTestFilePair()

    with lava.connection.get_smb_connection(f'{tc.prefix.conn}/smb/{name}', realm=tc.realm) as conn:

        # ------------------------------
        # Try getting a file from SMB
        with local_file1.open('wb') as fp:
            conn.retrieve_file(SMB_SERVICE_NAME, 'lava/hello.txt', fp)

        assert local_file1.is_file()
        assert local_file1.read_text() == smb_hello_file

        # ------------------------------
        # Try putting a file to SMB
        with (SMB_SHARED_DIR / 'lava/hello.txt').open('rb') as fp:
            conn.store_file(SMB_SERVICE_NAME, file2.remote, fp)
        # Check it appeared on local mirror
        assert file2.local.is_file()
        assert file2.local.read_text() == smb_hello_file

        # ------------------------------
        # Try renaming a file
        conn.rename(SMB_SERVICE_NAME, file2.remote, file3.remote)
        assert not file2.local.exists()
        assert file3.local.is_file()

        # ------------------------------
        # Try deleting a file
        conn.delete_files(SMB_SERVICE_NAME, file3.remote)
        assert not file3.local.exists()

        # ------------------------------
        # Try deleting files with a wildcard
        files = [SMBTestFilePair(suffix='.del') for _ in range(3)]
        # Create some files to delete by suffix pattern
        for f in files:
            with (SMB_SHARED_DIR / 'lava/hello.txt').open('rb') as fp:
                conn.store_file(SMB_SERVICE_NAME, f.remote, fp)
            assert f.local.is_file()
        conn.delete_files(SMB_SERVICE_NAME, 'lava/*.del')
        for f in files:
            assert not f.local.exists()
        # Make sure we didn't delete something we shouldn't
        assert len(conn.list_path(SMB_SERVICE_NAME, 'lava', pattern='hello.txt')) == 1


# ------------------------------------------------------------------------------
@pytest.mark.local
@pytest.mark.parametrize('name', SMB_CONNECTORS)
def test_delete_dir_fail(name, tc):
    dir1 = SMBTestFilePair(suffix='.d')
    with lava.connection.get_smb_connection(f'{tc.prefix.conn}/smb/{name}', realm=tc.realm) as conn:
        conn.create_directory(SMB_SERVICE_NAME, dir1.remote)
        assert dir1.local.is_dir()

        # Try deleting a dir as if it was a file
        with pytest.raises(SMBOperationError, match='Cannot delete'):
            conn.delete_files(SMB_SERVICE_NAME, dir1.remote)
        assert dir1.local.is_dir()


# ------------------------------------------------------------------------------
@pytest.mark.local
@pytest.mark.parametrize('name', SMB_CONNECTORS)
def test_smb_echo(name: str, tc):
    with lava.connection.get_smb_connection(f'{tc.prefix.conn}/smb/{name}', realm=tc.realm) as conn:
        assert conn.echo() == NTStatus.STATUS_SUCCESS


# ------------------------------------------------------------------------------
@pytest.mark.local
@pytest.mark.parametrize('name', SMB_CONNECTORS)
def test_conn_closed(name: str, tc):
    conn = lava.connection.get_smb_connection(f'{tc.prefix.conn}/smb/{name}', realm=tc.realm)
    conn.close()
    assert conn.close() is None
    with pytest.raises(SMBConnectionError, match='Not connected'):
        conn.echo()
    with pytest.raises(SMBConnectionError, match='Not connected'):
        conn.list_path(SMB_SERVICE_NAME, '.')
    with pytest.raises(SMBConnectionError, match='Not connected'):
        conn.retrieve_file(SMB_SERVICE_NAME, 'lava/hello,txt', None)  # noqa
    with pytest.raises(SMBConnectionError, match='Not connected'):
        conn.store_file(SMB_SERVICE_NAME, 'lava/nothing', None)  # noqa
    with pytest.raises(SMBConnectionError, match='Not connected'):
        conn.delete_files(SMB_SERVICE_NAME, 'lava/nothing', None)  # noqa
    with pytest.raises(SMBConnectionError, match='Not connected'):
        conn.create_directory(SMB_SERVICE_NAME, 'lava/nothing')
    with pytest.raises(SMBConnectionError, match='Not connected'):
        conn.delete_directory(SMB_SERVICE_NAME, 'lava/nothing')
    with pytest.raises(SMBConnectionError, match='Not connected'):
        conn.rename(SMB_SERVICE_NAME, 'lava/ignore', 'lava/something')


# ------------------------------------------------------------------------------
@pytest.mark.parametrize(
    'ntstatus_code,expected',
    [
        (0xC000006A, NTStatus.STATUS_WRONG_PASSWORD),
        (1234, NTStatus.UNKNOWN),
    ],
)
def test_ntstatus(ntstatus_code, expected):
    assert NTStatus.lookup(ntstatus_code) == expected


# ------------------------------------------------------------------------------
def test_smbtimeouterror():
    with pytest.raises(SMBBaseError):
        raise SMBTimeoutError('whatever')


# ------------------------------------------------------------------------------
@pytest.mark.local
@pytest.mark.parametrize('name', SMB_CONNECTORS)
def test_smb_dir_exists(name: str, tc):
    dir1 = SMBTestFilePair(suffix='.d')
    with lava.connection.get_smb_connection(f'{tc.prefix.conn}/smb/{name}', realm=tc.realm) as conn:

        # First check the dir doesn't exist
        assert not smb_dir_exists(conn, SMB_SERVICE_NAME, dir1.remote)
        # Create it and check again
        conn.create_directory(SMB_SERVICE_NAME, dir1.remote)
        assert dir1.local.is_dir()
        assert smb_dir_exists(conn, SMB_SERVICE_NAME, dir1.remote)

        with pytest.raises(Exception, match='exists but is not a directory'):
            smb_dir_exists(conn, SMB_SERVICE_NAME, 'lava/hello.txt')


# ------------------------------------------------------------------------------
@pytest.mark.local
@pytest.mark.parametrize('name', SMB_CONNECTORS)
def test_smb_mkdirs(name: str, tc):
    dir1 = SMBTestFilePair(f'lava/{uuid4()}.d/wotcha.d')
    with lava.connection.get_smb_connection(f'{tc.prefix.conn}/smb/{name}', realm=tc.realm) as conn:
        smb_mkdirs(conn, SMB_SERVICE_NAME, dir1.remote)
        assert dir1.local.is_dir()

        # Check idempotence
        smb_mkdirs(conn, SMB_SERVICE_NAME, dir1.remote)
