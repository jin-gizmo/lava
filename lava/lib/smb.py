"""
SMB related utilities. Relies on pysmb and smbprotocol packages.

See:
    - pysmb: https://pysmb.readthedocs.io/en/latest/api/smb_SMBConnection.html
    - smbprotocol: https://github.com/jborean93/smbprotocol

"""

from __future__ import annotations

import fnmatch
import logging
import os.path
from abc import ABC, abstractmethod
from contextlib import contextmanager
from enum import Enum
from typing import BinaryIO

import smbclient
import smbclient.shutil
from smb.SMBConnection import SMBConnection
from smb.base import NotConnectedError, NotReadyError, SMBTimeout, SharedFile
from smb.smb_structs import OperationFailure, ProtocolError, UnsupportedFeature
from smbclient._io import SMBDirectoryIO
from smbprotocol.exceptions import (
    IOTimeout,
    SMBAuthenticationError,
    SMBConnectionClosed,
    SMBException,
    SMBLinkRedirectionError,
    SMBOSError,
    SMBResponseException,
    SMBUnsupportedFeature,
)
from smbprotocol.file_info import FileInformationClass

__author__ = 'Murray Andrews, Alex Boul'

SMB_JOB_PARAMS_REQUIRED_FIELDS = {'conn_id', 'share_name', 'path', 'file'}
SMB_JOB_PARAMS_OPTIONAL_FIELDS = {'basedir', 'jinja', 'timeout', 'vars'}

SMB_CLI = 'lava-smb'


# ------------------------------------------------------------------------------
class NTStatus(int, Enum):
    """
    NTStatus extension class that allows for reverse lookup.

    This does not contain every NTStatus code but contains all common and important ones.
    List comes from smbprotocol:
    https://github.com/jborean93/smbprotocol/blob/942b005fcf7462cf0c5fed25d15f0594bfc6bd54/src/smbprotocol/header.py#L38

    """

    STATUS_SUCCESS = 0x00000000
    STATUS_UNSUCCESSFUL = 0xC0000001
    STATUS_NETWORK_NAME_DELETED = 0xC00000C9
    STATUS_PENDING = 0x00000103
    STATUS_NOTIFY_CLEANUP = 0x0000010B
    STATUS_NOTIFY_ENUM_DIR = 0x0000010C
    STATUS_BUFFER_OVERFLOW = 0x80000005
    STATUS_NO_MORE_FILES = 0x80000006
    STATUS_END_OF_FILE = 0xC0000011
    STATUS_INVALID_EA_NAME = 0x80000013
    STATUS_EA_LIST_INCONSISTENT = 0x80000014
    STATUS_STOPPED_ON_SYMLINK = 0x8000002D
    STATUS_INVALID_INFO_CLASS = 0xC0000003
    STATUS_INFO_LENGTH_MISMATCH = 0xC0000004
    STATUS_INVALID_PARAMETER = 0xC000000D
    STATUS_NO_SUCH_FILE = 0xC000000F
    STATUS_INVALID_DEVICE_REQUEST = 0xC0000010
    STATUS_MORE_PROCESSING_REQUIRED = 0xC0000016
    STATUS_ACCESS_DENIED = 0xC0000022
    STATUS_BUFFER_TOO_SMALL = 0xC0000023
    STATUS_OBJECT_NAME_INVALID = 0xC0000033
    STATUS_OBJECT_NAME_NOT_FOUND = 0xC0000034
    STATUS_OBJECT_NAME_COLLISION = 0xC0000035
    STATUS_OBJECT_PATH_INVALID = 0xC0000039
    STATUS_OBJECT_PATH_NOT_FOUND = 0xC000003A
    STATUS_OBJECT_PATH_SYNTAX_BAD = 0xC000003B
    STATUS_SHARING_VIOLATION = 0xC0000043
    STATUS_EAS_NOT_SUPPORTED = 0xC000004F
    STATUS_EA_TOO_LARGE = 0xC0000050
    STATUS_NONEXISTENT_EA_ENTRY = 0xC0000051
    STATUS_NO_EAS_ON_FILE = 0xC0000052
    STATUS_EA_CORRUPT_ERROR = 0xC0000053
    STATUS_DELETE_PENDING = 0xC0000056
    STATUS_PRIVILEGE_NOT_HELD = 0xC0000061
    STATUS_WRONG_PASSWORD = 0xC000006A
    STATUS_LOGON_FAILURE = 0xC000006D
    STATUS_PASSWORD_EXPIRED = 0xC0000071
    STATUS_NONE_MAPPED = 0xC0000073
    STATUS_INSUFFICIENT_RESOURCES = 0xC000009A
    STATUS_PIPE_NOT_AVAILABLE = 0xC00000AC
    STATUS_PIPE_BUSY = 0xC00000AE
    STATUS_PIPE_DISCONNECTED = 0xC00000B0
    STATUS_PIPE_CLOSING = 0xC00000B1
    STATUS_IO_TIMEOUT = 0xC00000B5
    STATUS_FILE_IS_A_DIRECTORY = 0xC00000BA
    STATUS_NOT_SUPPORTED = 0xC00000BB
    STATUS_BAD_NETWORK_NAME = 0xC00000CC
    STATUS_REQUEST_NOT_ACCEPTED = 0xC00000D0
    STATUS_PIPE_EMPTY = 0xC00000D9
    STATUS_INTERNAL_ERROR = 0xC00000E5
    STATUS_DIRECTORY_NOT_EMPTY = 0xC0000101
    STATUS_NOT_A_DIRECTORY = 0xC0000103
    STATUS_CANCELLED = 0xC0000120
    STATUS_CANNOT_DELETE = 0xC0000121
    STATUS_FILE_CLOSED = 0xC0000128
    STATUS_PIPE_BROKEN = 0xC000014B
    STATUS_FS_DRIVER_REQUIRED = 0xC000019C
    STATUS_USER_SESSION_DELETED = 0xC0000203
    STATUS_INSUFF_SERVER_RESOURCES = 0xC0000205
    STATUS_NOT_FOUND = 0xC0000225
    STATUS_PATH_NOT_COVERED = 0xC0000257
    STATUS_DFS_UNAVAILABLE = 0xC000026D
    STATUS_NOT_A_REPARSE_POINT = 0xC0000275
    STATUS_SERVER_UNAVAILABLE = 0xC0000466

    UNKNOWN = -1

    # --------------------------------------------------------------------------
    @classmethod
    def lookup(cls, ntstatus_code: int) -> NTStatus:
        """Reverse lookup NTStatus by status code."""

        for status in iter(cls):
            if ntstatus_code == status.value:
                return status

        return cls.UNKNOWN


# ------------------------------------------------------------------------------
# Lava SMB exception classes
class SMBBaseError(Exception):
    """A base exception class for Lava SMB exceptions."""

    # --------------------------------------------------------------------------
    def __init__(self, *args, **kwargs):
        """Create a SMBBaseException."""

        # noinspection PyArgumentList
        super().__init__(*args, **kwargs)


class SMBTimeoutError(SMBBaseError):
    """An SMB timeout exception class."""

    # --------------------------------------------------------------------------
    def __init__(self, *args, **kwargs):
        """Create a SMBTimeoutError."""

        super().__init__(*args, **kwargs)


class SMBConnectionError(SMBBaseError):
    """An SMB connection error class."""

    # --------------------------------------------------------------------------
    def __init__(self, *args, **kwargs):
        """Create a SMBConnectionError."""

        super().__init__(*args, **kwargs)


class SMBOperationError(SMBBaseError):
    """An SMB operation error class."""

    # --------------------------------------------------------------------------
    def __init__(self, *args, ntstatus: int, description: str, **kwargs):
        """
        Create a SMBOperationError.

        :param ntstatus:    the NTStatus code sent back from the server
        :param description: a description of the error
        """

        super().__init__(*args, **kwargs)

        self.ntstatus = ntstatus
        self.description = description

    # --------------------------------------------------------------------------
    def __str__(self) -> str:
        """Represent error as a string."""

        return f'[NtStatus {NTStatus.lookup(self.ntstatus).name}] {self.description}'


# ------------------------------------------------------------------------------
class SMBFileAttributes(int, Enum):
    """File attributes enum that holds bitwise attribute definitions."""

    NORMAL: int
    READONLY: int
    HIDDEN: int
    SYSTEM: int
    DIRECTORY: int
    ARCHIVE: int
    TEMPORARY: int


class MSCIFSFileAttributes(SMBFileAttributes):
    """
    File attributes specific to the SMB servers implementing the MS-CIFS protocol.

    [MS-CIFS File Attributes]
    https://learn.microsoft.com/en-us/openspecs/windows_protocols/ms-cifs/6008aa8f-d2d8-4366-b775-b81aece05bb1
    """

    NORMAL: int = 0x00
    READONLY: int = 0x01
    HIDDEN: int = 0x02
    SYSTEM: int = 0x04
    VOLUME: int = 0x08
    DIRECTORY: int = 0x10
    ARCHIVE: int = 0x20
    TEMPORARY: int = 0x0100
    COMPRESSED: int = 0x0800

    # INCL_NORMAL is a special placeholder to include normal files
    # with other search attributes for list_path() operations.
    # It is not defined in the MS-CIFS specs.
    INCL_NORMAL = 0x10000


class MSFSCCFileAttributes(SMBFileAttributes):
    """
    File attributes specific to the SMB servers implementing the MS-FSCC standard.

    This standard is used by the MS-SMB2 protocol.

    [MS-FSCC File Attributes]
    https://learn.microsoft.com/en-us/openspecs/windows_protocols/ms-fscc/ca28ec38-f155-4768-81d6-4bfeb8586fc9
    """

    READONLY: int = 0x01
    HIDDEN: int = 0x02
    SYSTEM: int = 0x04
    VOLUME: int = 0x08
    DIRECTORY: int = 0x10
    ARCHIVE: int = 0x20
    NORMAL: int = 0x80
    TEMPORARY: int = 0x0100
    SPARSE_FILE: int = 0x0200
    REPARSE_POINT: int = 0x0400
    COMPRESSED: int = 0x0800
    OFFLINE: int = 0x1000
    NOT_CONTENT_INDEXED: int = 0x2000
    ENCRYPTED: int = 0x4000
    INTEGRITY_STREAM: int = 0x8000
    NO_SCRUB_DATA: int = 0x020000
    RECALL_ON_OPEN: int = 0x040000
    PINNED: int = 0x080000
    UNPINNED: int = 0x100000
    RECALL_ON_DATA_ACCESS: int = 0x400000


# ------------------------------------------------------------------------------
class SMBFile:
    """Contains information about a file or folder on a shared SMB device."""

    # --------------------------------------------------------------------------
    def __init__(
        self,
        create_time: float,
        last_access_time: float,
        last_write_time: float,
        last_attr_change_time: float,
        file_size: int,
        alloc_size: int,
        file_attributes: bin,
        filename: str,
        attributes_class: type[SMBFileAttributes],
        short_name: str = None,
        file_id: int = None,
    ):
        """
        Create an SMBFile object.

        :param create_time: timestamp in epoch seconds for when the file was created on the server
        :param last_access_time: timestamp in epoch seconds for when the file was last accessed
        :param last_write_time: timestamp in epoch seconds for when the file was last modified
        :param last_attr_change_time: timestamp in epoch seconds for when a files attributes changed
        :param file_size: the size of the number in number of bytes
        :param alloc_size: total number of bytes allocated to store the file
        :param short_name: a unicode string containing the short file name (usually in 8.3 notation)
        :param file_attributes: a bit representation of file attributes
        :param filename: a unicode string containing the file name
        :param file_id: an integer value representing the file reference number for the file
        """

        self.create_time = create_time
        self.last_access_time = last_access_time
        self.last_write_time = last_write_time
        self.last_attr_change_time = last_attr_change_time
        self.file_size = file_size
        self.alloc_size = alloc_size
        self.file_attributes = file_attributes
        self.short_name = short_name
        self.filename = filename
        self.file_id = file_id

        self._attribute_class = attributes_class

    # --------------------------------------------------------------------------
    def has_attribute(self, attribute: SMBFileAttributes) -> bool:
        """
        Determine whether a file or folder has a specific file attribute.

        :param attribute: the SMBCommonFileAttribute to check for
        :returns: a boolean which represents wheter the file or folder has the attribute
        """

        return bool(self.file_attributes & attribute.value)

    # --------------------------------------------------------------------------
    def get_readable_attributes(self) -> list[str]:
        """Get a list of human readable attributes."""

        return [att.name for att in self._attribute_class if self.has_attribute(att)]

    # --------------------------------------------------------------------------
    @property
    def is_directory(self) -> bool:
        """Determines whether the file is a directory."""

        return self.has_attribute(self._attribute_class.DIRECTORY)

    # --------------------------------------------------------------------------
    @property
    def is_read_only(self) -> bool:
        """Determines whether the file is read only."""

        return self.has_attribute(self._attribute_class.READONLY)

    # --------------------------------------------------------------------------
    @property
    def is_normal(self) -> bool:
        """
        Determines if the file is a normal file.

        Following pysmb definition as a file that is not read-only, archived,
        hidden, system or a directory. It ignores other attributes like compression,
        indexed, sparse, temporary and encryption.
        """

        return (
            self.file_attributes == self._attribute_class.NORMAL.value
            or self.file_attributes & 0xFF == 0
        )


# ------------------------------------------------------------------------------
class SMBSigningOptions(Enum):
    """SMB Signing Options."""

    SIGN_NEVER = 0
    SIGN_WHEN_SUPPORTED = 1
    SIGN_WHEN_REQUIRED = 2


# ------------------------------------------------------------------------------
class LavaSMBConnection(ABC):  # pragma: no cover
    """A standard interface for SMB connection types."""

    # --------------------------------------------------------------------------
    @abstractmethod
    def __enter__(self):
        """Context manager enter support."""
        pass

    # --------------------------------------------------------------------------
    @abstractmethod
    def __exit__(self, *args):
        """Context manager exit support."""
        pass

    # --------------------------------------------------------------------------
    @property
    @abstractmethod
    def connected(self) -> bool:
        """Whether the client has made a connection or not."""
        pass

    # --------------------------------------------------------------------------
    @abstractmethod
    def connect(self, ip: str = None, port: int = None, timeout: int = 60) -> None:
        """
        Connect to an SMB server.

        :param ip:          A IP address to use instead of the remote name.
        :param port:        A port to connect instead of the default (445).
        :param timeout:     A timeout for the request. Default is 30s.
        """
        pass

    # ------------------------------------------------------------------------------
    @abstractmethod
    def close(self) -> None:
        """Terminate the SMB connection and release any sources held by the socket."""
        pass

    # ------------------------------------------------------------------------------
    @abstractmethod
    def list_path(
        self,
        service_name: str,
        path: str,
        pattern: str = '*',
        timeout: int = 30,
        **kwargs,
    ) -> list[SMBFile]:
        """
        Retrieve a directory listing of files/folders at path.

        :param service_name: The name of the shared folder for the path.
        :param path:         Path relative to the service_name to list subfolders/files.
        :param pattern:      The filter to apply to the results before returning to the client.
        :param timeout:      A timeout for the request. Default is 30s.
        :returns: A list of SMBFile instances.
        """
        pass

    # ------------------------------------------------------------------------------
    @abstractmethod
    def get_attributes(self, service_name: str, path: str, timeout: int = 30) -> SMBFile:
        """
        Retrieve information about the file at path on the service_name.

        :param service_name: The name of the shared folder for the path.
        :param path:         Path of the file on the remote server. If the file cannot be
                             opened for reading, an SMBOperationError will be raised.
        :param timeout:      A timeout for the request. Default is 30s.
        :returns: A SMBFile instance containing the attributes of the file.
        """
        pass

    # ------------------------------------------------------------------------------
    @abstractmethod
    def retrieve_file(
        self,
        service_name: str,
        path: str,
        file_obj: BinaryIO,
        timeout: int = 30,
        **kwargs,
    ) -> tuple[int, int]:
        """
        Retrieve the contents of the file from SMB server and write contents to the file_obj.

        :param service_name: The name of the shared folder for the path.
        :param path:         Path of the file on the remote server. If the file cannot be
                             opened for reading, an SMBOperationError will be raised.
        :param file_obj:     A file-like object that has a write method. Data will be written
                             continuously to file_obj until EOF is received from the remote
                             service. In Python3, this file-like object must have a write method
                             which accepts a bytes parameter.
        :param timeout:      A timeout for the request. Default is 30s.
        :returns: A 2-element tuple of file attributes (a bitwise-OR of SMBFileAttributes
                  bits) of the file, and the number of bytes written to file_obj.
        """
        pass

    # ------------------------------------------------------------------------------
    @abstractmethod
    def store_file(
        self,
        service_name: str,
        path: str,
        file_obj: BinaryIO,
        timeout: int = 30,
        **kwargs,
    ) -> int:
        """
        Store the contents of the file_obj at path on the service_name.

        If the file already exists on the remote server, it will be truncated and overwritten.

        :param service_name: The name of the shared folder for the path.
        :param path:         Path of the file on the remote server. If the file cannot be
                             opened for writing, an SMBOperationError will be raised.
        :param file_obj:     A file-like object that has a write method. Data will be written
                             continuously to file_obj until EOF is received from the remote
                             service. In Python3, this file-like object must have a write method
                             which accepts a bytes parameter.
        :param timeout:      A timeout for the request. Default is 30s.
        :returns: The number of bytes uploaded.
        """
        pass

    # ------------------------------------------------------------------------------
    @abstractmethod
    def delete_files(
        self,
        service_name: str,
        path_file_pattern: str,
        delete_matching_folders: bool = False,
        timeout: int = 30,
    ) -> None:
        """
        Delete one or more regular files.

        It supports the use of wildcards in file names, allowing for deletion of multiple files,
        however these won't be in a single request as the smbprotocol library does have support yet.

        :param service_name:            Contains the name of the shared folder.
        :param path_file_pattern:       The pathname of the files/subfolders to be deleted, relative
                                        to the service_name.
                                        Wildcards may be used in th filename component of the path.
        :param delete_matching_folders: If True, delete subfolders that match the path pattern.
        :param timeout:                 A timeout for the request. Default is 30s.
        """
        pass

    # ------------------------------------------------------------------------------
    @abstractmethod
    def create_directory(self, service_name: str, path: str, timeout: int = 30) -> None:
        """
        Create a new directory path on the service_name.

        :param service_name: The name of the shared folder for the path.
        :param path:         Path of the file on the remote server. If the folder exists,
                             an SMBOperationError will be raised.
        :param timeout:      A timeout for the request. Default is 30s.
        """
        pass

    # ------------------------------------------------------------------------------
    @abstractmethod
    def delete_directory(self, service_name: str, path: str, timeout: int = 30) -> None:
        """
        Delete the empty folder at path on service_name.

        :param service_name: The name of the shared folder for the path.
        :param path:         Path of the dir on the remote server. If the dir does not exist or is
                             not empty, an FileNotFoundError or an OSError is raised respectively.
        :param timeout:      A timeout for the request. Default is 30s.
        """
        pass

    # ------------------------------------------------------------------------------
    @abstractmethod
    def rename(self, service_name: str, old_path: str, new_path: str, timeout: int = 30) -> None:
        """
        Rename a file or folder at old_path to new_path shared at service_name.

        Note: that this method cannot be used to rename file/folder across different shared folders.

        :param service_name: The name of the shared folder for the path.
        :param old_path:     The path of the folder/file to rename.
        :param new_path:     The new path of the file or folder.
        :param timeout:      A timeout for the request. Default is 30s.
        """
        pass

    # ------------------------------------------------------------------------------
    @abstractmethod
    def echo(self, timeout: int = 10) -> NTStatus:
        """
        Send echo request to SMB server.

        Can be used to actively test connectivity to the SMB server.

        :param timeout:        The timeout in seconds to wait for the Echo Response, default is 10.
        :returns:              An NTStatus.
        """
        pass


# ----------------------------------------------------------------------------------
class SMBProtocolConnection(LavaSMBConnection):
    """SMB Lava Connection class using the smbprotocol module."""

    log = logging.getLogger('lava.lib.smb.SMBProtocolConnection')
    _file_att_class = MSFSCCFileAttributes

    # --------------------------------------------------------------------------
    def __init__(
        self,
        username: str,
        password: str,
        my_name: str,
        remote_name: str,
        port: int = None,
        domain: str = '',
        use_ntlm_v2: bool = True,
        sign_options: SMBSigningOptions = SMBSigningOptions.SIGN_WHEN_REQUIRED,
        is_direct_tcp: bool = True,
        encrypt: bool = True,
    ) -> None:
        r"""
        Create a new SMBProtocolConnection instance.

        WARNING: Connecting with a domain may not be thread safe due to Singleton nature
        of smbclient.ClientConfig. If creating a connection with a domain in a multithreaded
        environment, ensure that proper thread safety measures are applied around the creation
        of class instances.

        :param username:     Username credential for SMB server login.
        :param password:     Password credential for SMB server login.
        :param my_name:      A friendly name to identity where the connection originated from.
                             Must not contain spaces any characters in ``\\/:*?";|+``.
        :param remote_name:  The remote name or IP of the server.
        :param port:         The port of the server, default uses is_direct_tcp to determine port.
        :param domain:       Domain for connecting to SMB servers via DFS. Connects direct if blank.
        :param use_ntlm_v2:  Whether to use NTMLv2 to connect, otherwise negotiate. Default is True.
        :param sign_options: Whether SMB messages will be signed. Default is SIGN_WHEN_REQUIRED.
        :param is_direct_tcp: Connect over TCP/IP port 445, else via NetBIOS over TCP/IP port 139.
        :param encrypt:      Whether to force encryption to remote server. Default is True.
        """

        self._username = username
        self._password = password
        self._my_name = my_name
        self._remote_name = remote_name
        self._domain = domain
        self._skip_dfs = not self._domain
        self._auth_protocol = 'ntlm' if use_ntlm_v2 else 'negotiate'
        self._require_signing = bool(sign_options.value)
        self._port = port or (445 if is_direct_tcp else 139)
        self._encrypt = encrypt

        self._conn_cache = {}
        self._host = None
        self._session = None

    # --------------------------------------------------------------------------
    def __enter__(self):
        """Context manager enter support."""
        return self

    # --------------------------------------------------------------------------
    def __exit__(self, *args):
        """Context manager exit support."""
        self.close()

    # --------------------------------------------------------------------------
    @contextmanager
    def _error_handler(self):
        """Handle and map module specific errors into generic SMBBaseExceptions."""

        try:
            yield

        except (SMBAuthenticationError, SMBLinkRedirectionError) as e:
            raise SMBConnectionError(e) from e

        except (IOTimeout, SMBConnectionClosed) as e:
            raise SMBTimeoutError(e) from e

        except SMBOSError as e:
            description = f"{e.strerror}: '{e.filename}'"
            if e.filename2:
                description += f" -> '{e.filename2}'"

            raise SMBOperationError(
                ntstatus=e.ntstatus,
                description=description,
            ) from e

        except SMBResponseException as e:
            raise SMBOperationError(
                ntstatus=e.status,
                description=e.message,
            ) from e

        except SMBUnsupportedFeature as e:
            raise SMBOperationError(
                ntstatus=NTStatus.STATUS_NOT_SUPPORTED,
                description=e.message,
            ) from e

        except SMBException as e:
            raise SMBBaseError(e) from e

    # --------------------------------------------------------------------------
    @property
    def connected(self) -> bool:
        """Whether the connection has made a connection or not."""

        return self._session and self._session.connection.transport.connected

    # --------------------------------------------------------------------------
    def _service_path(self, service_name: str, path: str) -> str:
        r"""
        Convert a fileshare service and a file path into a UNC path.

        :param service_name: The name of the shared folder for the path.
        :param path:         Path relative to the service_name.
        :returns: A UNC style SMB path, e.g. \\10.0.0.1\share\folder\file.txt
        """

        tmp_path = path.strip('\\/').replace('/', '\\')
        return rf'\\{self._host}\{service_name}\{tmp_path}'.rstrip('\\')

    # --------------------------------------------------------------------------
    def _search_with_pattern(
        self,
        service_name: str,
        path_file_pattern: str,
        include_directories: bool = False,
        group_directories: bool = True,
    ) -> tuple[list, list]:
        """
        Search fileshare path using a pattern.

        :param service_name:        Contains the name of the shared folder.
        :param path_file_pattern:   The pathname of the files/subfolders to be found, relative
                                    to the service_name.
                                    Wildcards may be used in the filename component of the path.
        :param include_directories: If True, include subfolders that match the path pattern.
        :param group_directories:   If True, files/dirs under a matching dir will be filtered out.
        :returns: A tuple containing a list of matching directories and a list of matching files.
        """

        # Converts the full UNC path of the path file pattern for searching
        service_path_pattern = self._service_path(service_name, path_file_pattern)
        split_path = service_path_pattern.split('\\')

        # Calculate the highest directory required for searching as top path
        # The highest path is the one where folder contains no '*' or '?' characters
        top_path, pos = None, 0
        for path_arg in split_path:
            if '*' in path_arg or '?' in path_arg:
                top_path = service_path_pattern[:pos].rstrip('\\')
                break

            pos += len(path_arg) + 1

        if top_path is None:
            top_path = '\\'.join(split_path[:-1])

        max_depth = len(split_path) - len(top_path.split('\\'))

        # Walk from the top dir through all files, adding any dirs/files which fit the pattern
        # Matching files will be deleted. It will try and perform the smallest number of requests
        # By not adding files or directories that are inside a directory marked for deletion
        with self._error_handler():
            files, dirs, ignore_dirs = set(), set(), set()
            for dirpath, dirnames, filenames in smbclient.walk(
                top_path, connection_cache=self._conn_cache, port=self._port
            ):
                # Avoids unintentionally deleting files in subdirectories that match the pattern
                subpath = dirpath[len(top_path) :].lstrip('\\')
                depth = len(subpath.split('\\') if subpath else [])
                if depth >= max_depth:
                    continue

                # If delete_matching_folders is true, mark matching folders for deletion too
                if include_directories:
                    for dirname in dirnames:
                        folder_path = dirpath + '\\' + dirname

                        # Skip subdirectories of trees that will be deleted
                        if dirpath in ignore_dirs and group_directories:
                            ignore_dirs.add(folder_path)
                            continue

                        # If a dir path matches the pattern, add it to the dir set for deletion
                        if fnmatch.fnmatch(folder_path, service_path_pattern):
                            dirs.add(folder_path)
                            ignore_dirs.add(folder_path)

                for filename in filenames:
                    file_path = dirpath + '\\' + filename

                    # Skip files in directories that will be deleted
                    if dirpath in ignore_dirs and group_directories:
                        continue

                    # If a file path matches the pattern, add it to the file set for deletion
                    if fnmatch.fnmatch(file_path, service_path_pattern):
                        files.add(file_path)

        return list(dirs), list(files)

    # --------------------------------------------------------------------------
    def _set_client_config(self) -> None:
        """Overwrite all smbprotocol.ClientConfig global config properties."""

        client_vars = {
            'client_guid': self._my_name.ljust(16)[0:16].encode(),
            'username': self._username,
            'password': self._password,
            'skip_dfs': self._skip_dfs,
            'auth_protocol': self._auth_protocol,
            'require_secure_negotiate': True,
            'domain_controller': self._domain,
        }

        # These should not be present in the global config for thread safety.
        # However they are required when connecting to a DFS share.
        if not self._domain:
            client_vars.pop('username')
            client_vars.pop('password')
            client_vars.pop('domain_controller')

        smbclient.ClientConfig(**client_vars)
        self.log.debug('Set SMB client config')

    # --------------------------------------------------------------------------
    def connect(self, ip: str = None, port: int = None, timeout: int = 60) -> None:
        """
        Connect to SMB server.

        :param ip:          A IP address to use instead of the remote name.
        :param port:        A port to connect instead of the default (445).
        :param timeout:     A timeout for the request. Default is 30s.
        """

        with self._error_handler():
            if self.connected:
                self.close()

            self._set_client_config()

            self._host = ip or self._remote_name
            self._port = port or self._port

            if self._domain and self._domain == self._host:
                raise SMBConnectionError(
                    'DFS domain and SMB remote name can not be the same, this will '
                    'cause an infinite loop when attempting to locate files. If they '
                    'are named the same consider setting the host to an IP address.'
                )

            try:
                self._session = smbclient.register_session(
                    server=self._host,
                    port=self._port,
                    username=self._username,
                    password=self._password,
                    encrypt=self._encrypt,
                    auth_protocol=self._auth_protocol,
                    require_signing=self._require_signing,
                    connection_timeout=timeout,
                    connection_cache=self._conn_cache,
                )
            except ValueError as e:
                raise SMBConnectionError(e)

            self.log.debug('SMB Connection successful')

    # ------------------------------------------------------------------------------
    def close(self) -> None:
        """Terminate the SMB connection and release any sources held by the socket."""

        if not self.connected:
            return

        for conn in self._conn_cache.values():
            conn.disconnect(close=True)

        self.log.debug('Closed SMB all connections, sessions and sockets')

    # ------------------------------------------------------------------------------
    def list_path(
        self,
        service_name: str,
        path: str,
        pattern: str = '*',
        timeout: int = 30,
        search: int = None,
    ) -> list[SMBFile]:
        """
        Retrieve a directory listing of files/folders at path.

        :param service_name: The name of the shared folder for the path.
        :param path:         Path relative to the service_name to list subfolders/files.
        :param pattern:      The filter to apply to the results before returning to the client.
        :param timeout:      A timeout for the request. Default is 30s.
        :param search:       Allows a search=0xYYY to list files with specific SMBFile attributes.
        :returns: A list of SMBFile instances.
        """

        if not self.connected:
            raise SMBConnectionError('Not connected to SMB server')

        if search is None:
            search = (
                self._file_att_class.READONLY
                | self._file_att_class.HIDDEN
                | self._file_att_class.SYSTEM
                | self._file_att_class.DIRECTORY
                | self._file_att_class.ARCHIVE
                | self._file_att_class.NORMAL
            )

        with self._error_handler():
            dir_path = self._service_path(service_name, path)
            with SMBDirectoryIO(
                dir_path, share_access='rwd', connection_cache=self._conn_cache, port=self._port
            ) as fd:
                fd: SMBDirectoryIO

                output_files = []
                for dir_info in fd.query_directory(
                    pattern, FileInformationClass.FILE_ID_FULL_DIRECTORY_INFORMATION
                ):
                    filename = dir_info['file_name'].get_value().decode('utf-16-le')
                    if filename in ['.', '..']:
                        continue

                    file = SMBFile(
                        create_time=dir_info['creation_time'].get_value().timestamp(),
                        last_access_time=dir_info['last_access_time'].get_value().timestamp(),
                        last_write_time=dir_info['last_write_time'].get_value().timestamp(),
                        last_attr_change_time=dir_info['change_time'].get_value().timestamp(),
                        file_size=dir_info['end_of_file'].get_value(),
                        alloc_size=dir_info['allocation_size'].get_value(),
                        file_attributes=dir_info['file_attributes'].get_value(),
                        attributes_class=self._file_att_class,
                        filename=filename,
                        file_id=dir_info['file_id'].get_value(),
                    )
                    if search & file.file_attributes:
                        output_files.append(file)

        self.log.debug("Listed directory of '%s'", dir_path)
        return output_files

    # ------------------------------------------------------------------------------
    def get_attributes(self, service_name: str, path: str, timeout: int = 30) -> SMBFile:
        """
        Retrieve information about the file at path on the service_name.

        :param service_name: The name of the shared folder for the path.
        :param path:         Path of the file on the remote server. If the file cannot be
                             opened for reading, an SMBOperationError will be raised.
        :param timeout:      A timeout for the request. Default is 30s.
        :returns: A SMBFile instance containing the attributes of the file.
        """

        unc_path = self._service_path(service_name, path)
        tmp_path = path.strip('\\/').replace('/', '\\')

        dir_path, file_name = tmp_path.rsplit('\\', 1)
        files = self.list_path(service_name, dir_path, file_name, timeout)
        if len(files) != 1:
            raise SMBOperationError(
                ntstatus=NTStatus.STATUS_OBJECT_PATH_NOT_FOUND,
                description=f"No files or directories exist at the path '{unc_path}'",
            )

        return files[0]

    # ------------------------------------------------------------------------------
    def retrieve_file(
        self, service_name: str, path: str, file_obj: BinaryIO, timeout: int = 30, **kwargs
    ) -> tuple[int, int]:
        """
        Retrieve the contents of the file from SMB server and write contents to the file_obj.

        :param service_name:  The name of the shared folder for the path.
        :param path:          Path of the file on the remote server. If the file cannot be
                              opened for reading, an SMBOperationError will be raised.
        :param file_obj:      A file-like object that has a write method. Data will be written
                              continuously to file_obj until EOF is received from the remote
                              service. In Python3, this file-like object must have a write method
                              which accepts a bytes parameter.
        :param timeout:       A timeout for the request. Default is 30s.
        :returns: A 2-element tuple of file attributes (a bitwise-OR of SMBFileAttributes
                  bits) of the file, and the number of bytes written to file_obj.
        """

        if not self.connected:
            raise SMBConnectionError('Not connected to SMB server')

        attrs = self.get_attributes(service_name, path, timeout)
        with self._error_handler():
            remote_filepath = self._service_path(service_name, path)

            with smbclient.open_file(
                remote_filepath,
                'rb',
                connection_cache=self._conn_cache,
                port=self._port,
            ) as remote_file:
                smbclient.shutil.copyfileobj(remote_file, file_obj)

                self.log.debug("Retrieved file from '%s'", remote_filepath)
                return (
                    attrs.file_attributes,
                    file_obj.tell(),
                )

    # ------------------------------------------------------------------------------
    def store_file(
        self, service_name: str, path: str, file_obj: BinaryIO, timeout: int = 30, **kwargs
    ) -> int:
        """
        Store the contents of the file_obj at path on the service_name.

        If the file already exists on the remote server, it will be truncated and overwritten.

        :param service_name:  The name of the shared folder for the path.
        :param path:          Path of the file on the remote server. If the file cannot be
                              opened for reading, an SMBOperationError will be raised.
        :param file_obj:      A file-like object that has a write method. Data will be written
                              continuously to file_obj until EOF is received from the remote
                              service. In Python3, this file-like object must have a write method
                              which accepts a bytes parameter.
        :param timeout:       A timeout for the request. Default is 30s.
        :returns: The number of bytes uploaded.
        """

        if not self.connected:
            raise SMBConnectionError('Not connected to SMB server')

        with self._error_handler():
            remote_filepath = self._service_path(service_name, path)

            # Open file in SMB server for writing
            with smbclient.open_file(
                remote_filepath, 'wb', connection_cache=self._conn_cache, port=self._port
            ) as remote_file:
                # Copy local file contents to remote file in chunks
                smbclient.shutil.copyfileobj(file_obj, remote_file)

                self.log.debug("Stored file to '%s'", remote_filepath)
                return file_obj.tell()

    # ------------------------------------------------------------------------------
    def delete_files(
        self,
        service_name: str,
        path_file_pattern: str,
        delete_matching_folders: bool = False,
        timeout: int = 30,
    ) -> None:
        """
        Delete one or more regular files.

        It supports the use of wildcards in file names, allowing for deletion of multiple files,
        however these won't be in a single request as the smbprotocol library does have support yet.

        :param service_name:            Contains the name of the shared folder.
        :param path_file_pattern:       The pathname of the files/subfolders to be deleted, relative
                                        to the service_name.
                                        Wildcards may be used in th filename component of the path.
        :param delete_matching_folders: If True, delete subfolders that match the path pattern.
        :param timeout:                 A timeout for the request. Default is 30s.
        """

        if not self.connected:
            raise SMBConnectionError('Not connected to SMB server')

        with self._error_handler():
            dirs, files = self._search_with_pattern(
                service_name,
                path_file_pattern,
                delete_matching_folders,
            )

            if (
                len(dirs) == 1
                and not ('*' in path_file_pattern or '?' in path_file_pattern)
                and dirs[0] == self._service_path(service_name, path_file_pattern)
            ):
                raise SMBOperationError(
                    ntstatus=NTStatus.STATUS_FILE_IS_A_DIRECTORY,
                    description=f'Cannot delete folder {path_file_pattern} on {service_name}, '
                    'please use delete_directory() method instead or add "/*" to the path if '
                    'you wish to delete all files in the folder.',
                )

            # Delete any directories that match the pattern
            for path in dirs:
                smbclient.shutil.rmtree(path, connection_cache=self._conn_cache, port=self._port)
                self.log.debug("Deleted directory '%s'", path)

            # Delete any files that match the pattern
            for path in files:
                smbclient.remove(path, connection_cache=self._conn_cache, port=self._port)
                self.log.debug("Deleted file '%s'", path)

    # ------------------------------------------------------------------------------
    def create_directory(self, service_name: str, path: str, timeout: int = 30) -> None:
        """
        Create a new directory path on the service_name.

        :param service_name: The name of the shared folder for the path.
        :param path:         Path of the file on the remote server. If the folder exists,
                             an SMBOperationError will be raised.
        :param timeout:      A timeout for the request. Default is 30s.
        """

        if not self.connected:
            raise SMBConnectionError('Not connected to SMB server')

        with self._error_handler():
            unc_path = self._service_path(service_name, path)
            smbclient.mkdir(unc_path, connection_cache=self._conn_cache, port=self._port)

            self.log.debug("Created directory '%s'", unc_path)

    # ------------------------------------------------------------------------------
    def delete_directory(self, service_name: str, path: str, timeout: int = 30) -> None:
        """
        Delete the empty folder at path on service_name.

        :param service_name: The name of the shared folder for the path.
        :param path:         Path of the dir on the remote server. If the dir does not exist or is
                             not empty, an FileNotFoundError or an OSError is raised respectively.
        :param timeout:      A timeout for the request. Default is 30s.
        """

        if not self.connected:
            raise SMBConnectionError('Not connected to SMB server')

        with self._error_handler():
            unc_path = self._service_path(service_name, path)
            smbclient.rmdir(unc_path, connection_cache=self._conn_cache, port=self._port)

            self.log.debug("Deleted directory '%s'", unc_path)

    # ------------------------------------------------------------------------------
    def rename(self, service_name: str, old_path: str, new_path: str, timeout: int = 30) -> None:
        """
        Rename a file or folder at old_path to new_path shared at service_name.

        Note: that this method cannot be used to rename file/folder across different shared folders.

        :param service_name: The name of the shared folder for the path.
        :param old_path:     The path of the folder/file to rename.
        :param new_path:     The new path of the file or folder.
        :param timeout:      A timeout for the request. Default is 30s.
        """

        if not self.connected:
            raise SMBConnectionError('Not connected to SMB server')

        with self._error_handler():
            o_unc_path = self._service_path(service_name, old_path)
            n_unc_path = self._service_path(service_name, new_path)
            smbclient.rename(
                o_unc_path, n_unc_path, connection_cache=self._conn_cache, port=self._port
            )

            self.log.debug("Renamed resource from '%s' to '%s'", old_path, new_path)

    # ------------------------------------------------------------------------------
    def echo(self, timeout: int = 10) -> NTStatus:
        """
        Send echo request to SMB server.

        Can be used to actively test connectivity to the SMB server.

        :param timeout:        The timeout in seconds to wait for the Echo Response, Default is 10.
        :returns:              An NTStatus.
        """

        if not self.connected:
            raise SMBConnectionError('Not connected to SMB server')

        try:
            with self._error_handler():
                conn = self._session.connection
                conn.echo(self._session.session_id, timeout)
                self.log.debug('Received echo back from server')

                return NTStatus.STATUS_SUCCESS
        except SMBOperationError as e:
            self.log.error(e)
            return NTStatus.lookup(e.ntstatus)


# ----------------------------------------------------------------------------------
class PySMBConnection(LavaSMBConnection):
    """SMB Lava Connection class using the pysmb module."""

    LOG = logging.getLogger('lava.lib.smb.PySMBConnection')
    _file_att_class = MSCIFSFileAttributes

    # --------------------------------------------------------------------------
    def __init__(
        self,
        username: str,
        password: str,
        my_name: str,
        remote_name: str,
        domain: str = '',
        use_ntlm_v2: bool = True,
        sign_options: SMBSigningOptions = SMBSigningOptions.SIGN_WHEN_REQUIRED,
        is_direct_tcp: bool = True,
    ) -> None:
        r"""
        Create a new PySMBConnection instance.

        :param username:     Username credential for SMB server login.
        :param password:     Password credential for SMB server login.
        :param my_name:      A friendly name to identity where the connection originated from.
                             Must not contain spaces any characters in ``\\/:*?";|+``.
        :param remote_name:  The remote name or IP of the server.
        :param domain:       Domain for connecting to SMB servers.
        :param use_ntlm_v2:  Whether to use NTMLv2 to connect, otherwise negotiate. Default is True.
        :param sign_options: Whether SMB messages will be signed. Default is SIGN_WHEN_REQUIRED.
        :param is_direct_tcp: Connect over TCP/IP port 445, else via NetBIOS over TCP/IP port 139.
        """

        self._username = username
        self._password = password
        self._my_name = my_name
        self._remote_name = remote_name
        self._domain = domain
        self._use_ntlm_v2 = use_ntlm_v2
        self._sign_option = sign_options.value
        self._is_direct_tcp = is_direct_tcp
        self._port = 445 if is_direct_tcp else 139

        self._connection = SMBConnection(
            username=self._username,
            password=self._password,
            my_name=self._my_name,
            remote_name=self._remote_name,
            domain=self._domain,
            use_ntlm_v2=self._use_ntlm_v2,
            sign_options=self._sign_option,
            is_direct_tcp=self._is_direct_tcp,
        )

        self._host: str | None = None

    # --------------------------------------------------------------------------
    def __enter__(self):
        """Context manager enter support."""
        return self

    # --------------------------------------------------------------------------
    def __exit__(self, *args):
        """Context manager exit support."""
        self.close()

    # --------------------------------------------------------------------------
    @contextmanager
    def _error_handler(self):
        """Handle and map module specific errors into generic SMBBaseExceptions."""

        try:
            yield
        except (NotConnectedError, NotReadyError, ProtocolError) as e:
            raise SMBConnectionError(str(e).split('\n')[0]) from e
        except SMBTimeout as e:
            raise SMBTimeoutError(str(e)) from e
        except OperationFailure as e:
            raise SMBOperationError(
                ntstatus=next(m.status for m in e.smb_messages if m.status > 0),
                description=e.message,
            ) from e
        except UnsupportedFeature as e:
            raise SMBOperationError(
                ntstatus=NTStatus.STATUS_NOT_SUPPORTED,
                description=str(e),
            ) from e

    # --------------------------------------------------------------------------
    def _full_path(self, service_name, path) -> str:
        r"""
        Convert a fileshare service and a file path into a UNC path.

        :param service_name: The name of the shared folder for the path.
        :param path:         Path relative to the service_name.
        :returns: A UNC style SMB path, e.g. \\10.0.0.1\share\folder\file.txt
        """

        tmp_path = path.strip('\\/').replace('/', '\\')
        return rf'\\{self._host}\{service_name}\{tmp_path}'.rstrip('\\')

    # ------------------------------------------------------------------------------
    @property
    def connected(self) -> bool:
        """Whether the connection has made a connection or not."""

        return bool(self._connection.sock)

    # ------------------------------------------------------------------------------
    def connect(self, ip: str = None, port: int = None, timeout: int = 60) -> None:
        """
        Connect to SMB server.

        :param ip:          A IP address to use instead of the remote name.
        :param port:        A port to connect instead of the default (445).
        :param timeout:     A timeout for the request. Default is 30s.
        """

        with self._error_handler():
            self._host = ip or self._remote_name
            self._port = port or self._port

            success = self._connection.connect(
                ip=self._host,
                port=self._port,
                timeout=timeout,
            )

            if not success:
                raise SMBConnectionError(f'Failed to connect to {self._host}:{self._port}')

            self.LOG.debug('SMB Connection succesful')

    # ------------------------------------------------------------------------------
    def close(self) -> None:
        """Terminate the SMB connection and release any sources held by the socket."""

        with self._error_handler():
            self._connection.close()

    # ------------------------------------------------------------------------------
    def list_path(
        self,
        service_name: str,
        path: str,
        pattern: str = '*',
        timeout: int = 30,
        search: int = None,
    ) -> list[SMBFile]:
        """
        Retrieve a directory listing of files/folders at path.

        :param service_name: The name of the shared folder for the path.
        :param path:         Path relative to the service_name to list subfolders/files.
        :param pattern:      The filter to apply to the results before returning to the client.
        :param timeout:      A timeout for the request. Default is 30s.
        :param search:       Allows a search=0xYYY to list files with specific SMBFile attributes.
        :returns: A list of SMBFile instances.
        """

        if search is None:
            search = (
                self._file_att_class.READONLY
                | self._file_att_class.HIDDEN
                | self._file_att_class.SYSTEM
                | self._file_att_class.DIRECTORY
                | self._file_att_class.ARCHIVE
                | self._file_att_class.INCL_NORMAL
            )

        output_files = []
        with self._error_handler():
            path_list: list[SharedFile] = self._connection.listPath(
                service_name=service_name,
                path=path,
                search=search,
                pattern=pattern,
                timeout=timeout,
            )

            for smb_file in path_list:
                file = SMBFile(
                    create_time=smb_file.create_time,
                    last_access_time=smb_file.last_access_time,
                    last_write_time=smb_file.last_write_time,
                    last_attr_change_time=smb_file.last_attr_change_time,
                    file_size=smb_file.file_size,
                    alloc_size=smb_file.alloc_size,
                    file_attributes=smb_file.file_attributes,
                    attributes_class=self._file_att_class,
                    filename=smb_file.filename,
                    short_name=smb_file.short_name,
                    file_id=smb_file.file_id,
                )

                if file.filename not in ('.', '..'):
                    output_files.append(file)

        self.LOG.debug(r"Listed directory of '%s'", self._full_path(service_name, path))
        return output_files

    # ------------------------------------------------------------------------------
    def get_attributes(self, service_name: str, path: str, timeout: int = 30) -> SMBFile:
        """
        Retrieve information about the file at path on the service_name.

        :param service_name: The name of the shared folder for the path.
        :param path:         Path of the file on the remote server. If the file cannot be
                             opened for reading, an SMBOperationError will be raised.
        :param timeout:      A timeout for the request. Default is 30s.
        :returns: A SMBFile instance containing the attributes of the file.
        """

        with self._error_handler():
            smb_file = self._connection.getAttributes(service_name, path, timeout)

            return SMBFile(
                create_time=smb_file.create_time,
                last_access_time=smb_file.last_access_time,
                last_write_time=smb_file.last_write_time,
                last_attr_change_time=smb_file.last_attr_change_time,
                file_size=smb_file.file_size,
                alloc_size=smb_file.alloc_size,
                file_attributes=smb_file.file_attributes,
                attributes_class=self._file_att_class,
                filename=smb_file.filename,
                short_name=smb_file.short_name,
                file_id=smb_file.file_id,
            )

    # ------------------------------------------------------------------------------
    def retrieve_file(
        self, service_name: str, path: str, file_obj: BinaryIO, timeout: int = 30, **kwargs
    ) -> tuple[int, int]:
        """
        Retrieve the contents of the file from SMB server and write contents to the file_obj.

        :param service_name:  The name of the shared folder for the path.
        :param path:          Path of the file on the remote server. If the file cannot be
                              opened for reading, an SMBOperationError will be raised.
        :param file_obj:      A file-like object that has a write method. Data will be written
                              continuously to file_obj until EOF is received from the remote
                              service. In Python3, this file-like object must have a write method
                              which accepts a bytes parameter.
        :param timeout:       A timeout for the request. Default is 30s.
        :returns: A 2-element tuple of file attributes (a bitwise-OR of SMB_FILE_ATTRIBUTE_xxx
                  bits) of the file, and the number of bytes written to file_obj.
        """

        with self._error_handler():
            file_atts, file_size = self._connection.retrieveFile(
                service_name=service_name,
                path=path,
                file_obj=file_obj,
                timeout=timeout,
                show_progress=kwargs.get('show_progress', False),
                tqdm_kwargs=kwargs.get('tqdm_kwargs', {}),
            )

            remote_filepath = self._full_path(service_name, path)
            self.LOG.debug("Retrieved file from '%s'", remote_filepath)
            return file_atts, file_size

    # ------------------------------------------------------------------------------
    def store_file(
        self, service_name: str, path: str, file_obj: BinaryIO, timeout: int = 30, **kwargs
    ) -> int:
        """
        Store the contents of the file_obj at path on the service_name.

        If the file already exists on the remote server, it will be truncated and overwritten.

        :param service_name:  The name of the shared folder for the path.
        :param path:          Path of the file on the remote server. If the file cannot be
                              opened for reading, an SMBOperationError will be raised.
        :param file_obj:      A file-like object that has a write method. Data will be written
                              continuously to file_obj until EOF is received from the remote
                              service. In Python3, this file-like object must have a write method
                              which accepts a bytes parameter.
        :param timeout:       A timeout for the request. Default is 30s.
        :param kwargs:        Allows for pysmb args 'show_progress' (bool) and 'tqdm_kwargs' (dict)
                              See docs:
        :returns: The number of bytes uploaded.
        """

        with self._error_handler():
            file_size = self._connection.storeFile(
                service_name=service_name,
                path=path,
                file_obj=file_obj,
                timeout=timeout,
                show_progress=kwargs.get('show_progress', False),
                tqdm_kwargs=kwargs.get('tqdm_kwargs', {}),
            )

            remote_filepath = self._full_path(service_name, path)
            self.LOG.debug("Stored file to '%s'", remote_filepath)
            return file_size

    # ------------------------------------------------------------------------------
    def delete_files(
        self,
        service_name: str,
        path_file_pattern: str,
        delete_matching_folders: bool = False,
        timeout: int = 30,
    ) -> None:
        """
        Delete one or more regular files.

        It supports the use of wildcards in file names, allowing for deletion of multiple files,
        however these won't be in a single request as the smbprotocol library does have support yet.

        :param service_name:            Contains the name of the shared folder.
        :param path_file_pattern:       The pathname of the files/subfolders to be deleted, relative
                                        to the service_name.
                                        Wildcards may be used in th filename component of the path.
        :param delete_matching_folders: If True, delete subfolders that match the path pattern.
        :param timeout:                 A timeout for the request. Default is 30s.
        """

        with self._error_handler():
            self._connection.deleteFiles(
                service_name=service_name,
                path_file_pattern=path_file_pattern,
                delete_matching_folders=delete_matching_folders,
                timeout=timeout,
            )

    # ------------------------------------------------------------------------------
    def create_directory(self, service_name: str, path: str, timeout: int = 30) -> None:
        """
        Create a new directory path on the service_name.

        :param service_name: The name of the shared folder for the path.
        :param path:         Path of the file on the remote server. If the folder exists,
                             an SMBOperationError will be raised.
        :param timeout:      A timeout for the request. Default is 30s.
        """

        with self._error_handler():
            self._connection.createDirectory(service_name, path, timeout)

            unc_path = self._full_path(service_name, path)
            self.LOG.debug("Created directory '%s'", unc_path)

    # ------------------------------------------------------------------------------
    def delete_directory(self, service_name: str, path: str, timeout: int = 30) -> None:
        """
        Delete the empty folder at path on service_name.

        :param service_name: The name of the shared folder for the path.
        :param path:         Path of the dir on the remote server. If the dir does not exist or is
                             not empty, an FileNotFoundError or an OSError is raised respectively.
        :param timeout:      A timeout for the request. Default is 30s.
        """

        with self._error_handler():
            self._connection.deleteDirectory(service_name, path, timeout)

            unc_path = self._full_path(service_name, path)
            self.LOG.debug("Deleted directory '%s'", unc_path)

    # ------------------------------------------------------------------------------
    def rename(self, service_name: str, old_path: str, new_path: str, timeout: int = 30) -> None:
        """
        Rename a file or folder at old_path to new_path shared at service_name.

        Note: that this method cannot be used to rename file/folder across different shared folders.

        :param service_name: The name of the shared folder for the path.
        :param old_path:     The path of the folder/file to rename.
        :param new_path:     The new path of the file or folder.
        :param timeout:      A timeout for the request. Default is 30s.
        """

        with self._error_handler():
            self._connection.rename(service_name, old_path, new_path, timeout)

    # ------------------------------------------------------------------------------
    def echo(self, timeout: int = 10) -> NTStatus:
        """
        Send echo request to SMB server.

        Can be used to actively test connectivity to the SMB server.

        :param timeout:        The timeout in seconds to wait for the Echo Response, Default is 10.
        :returns:              An NTStatus.
        """

        try:
            with self._error_handler():
                self._connection.echo(b'', timeout)
                self.LOG.debug('Received echo back from server')

                return NTStatus.STATUS_SUCCESS
        except SMBOperationError as e:
            return NTStatus.lookup(e.ntstatus)


# ------------------------------------------------------------------------------
def smb_dir_exists(conn: LavaSMBConnection, share_name: str, path: str) -> bool:
    """
    Check that the specified directory exists on the given SMB file share.

    :param conn:        An SMB connection.
    :param share_name:  The SMB share name.
    :param path:        Target directory.

    :return:            True if it exists, False otherwise.

    :raise Exception:   If the target exists but is not a directory.
    """

    try:
        attr = conn.get_attributes(share_name, path)
    except SMBOperationError:
        # Assume this means it doesn't exist
        return False

    if attr.is_directory:
        return True

    raise Exception(f'{share_name}:{path} exists but is not a directory')


# ------------------------------------------------------------------------------
def smb_mkdirs(conn: LavaSMBConnection, share_name: str, path: str) -> None:
    """
    Create a directory on an SMB file share if it doesn't already exist.

    All necessary parent directories will also be created.

    :param conn:        An SMB connection.
    :param share_name:  The SMB share name.
    :param path:        Target directory.
    """

    parent, _ = os.path.split(path)

    if smb_dir_exists(conn, share_name, path):
        return

    if parent and not smb_dir_exists(conn, share_name, parent):
        smb_mkdirs(conn, share_name, parent)

    conn.create_directory(share_name, path)
