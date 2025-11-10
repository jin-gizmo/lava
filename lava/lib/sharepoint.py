"""
Model a SharePoint site.

Uses the Graph API.

"""

# TODO: We need to get rid of the dead code.
# ruff: noqa: ERA001

# TODO: provide count of items currently deleted in replace list.
#       So we can track where we are at with full batch delete.

from __future__ import annotations

import csv
import datetime
import json
import logging
import os
from collections.abc import Iterable
from contextlib import suppress
from fnmatch import fnmatchcase
from time import sleep
from typing import Any

import dateutil.parser
import dateutil.tz
from requests import Request, Response, Session, post
from requests.exceptions import ConnectionError, ProxyError, ReadTimeout  # noqa A004

__author__ = 'Chris Donoghue'

MAX_DL_FILESIZE = 4000000

MS_LOGIN_URL = 'https://login.microsoftonline.com'
MS_GRAPH_API_URL = 'https://graph.microsoft.com/v1.0'

API_TIMEOUT = (5, 150)  # Connect timeout, Read timeout

THROTTLING_LIMIT = 10
THROTTLING_BACKOFF_SECONDS = 15
THROTTLING_BACKOFF_LIMIT = 6
THROTTLING_MAX_DELAY = 661
GRAPH_API_HARD_ERROR_WAIT_SECONDS = 240
API_RETRY_THRESHOLD = 5
TOKEN_COUNT_THRESHOLD = 5
# Chrome browser on Windows 10
FAKE_HTTP_USERAGENT = (
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
    '(KHTML, like Gecko) Chrome/76.0.3809.132 Safari/537.36'
)
UPLOAD_SESSION_FRAGMENT_SIZE = 327680

APP_LOCAL_TZ = dateutil.tz.tzlocal()

NULL_LOGGER = logging.getLogger('NULL')
NULL_LOGGER.addHandler(logging.NullHandler())

# MS docs for graph api say to come back later of these HTTP status
RETRY_STATUS_CODES = (
    429,  # Too Many Requests
    502,  # Bad Gateway
    503,  # Service Unavailable
    504,  # Gateway Timeout
    509,  # Bandwidth Limit Exceeded
)


class KeyExists:
    """Used for object search function."""

    pass


# ..............................................................................
# region Utilities
# ..............................................................................


# ------------------------------------------------------------------------------
def dump_request(suf: str, r: Response, req: Any = None) -> None:
    """
    For given requests response value dump the header and JSON payload to a file.

    For a given req python object dump to json file debug MS Graph API (REST
    API) purpose only.

    :param suf:     suffix of dump file that is written out.
    :param r:       requests response object
    :param req:     python payload that the requests payload

    """

    datepref = datetime_with_utc_tz().astimezone(APP_LOCAL_TZ).replace(microsecond=0).isoformat()
    if r:
        with open(f'request_dump/{datepref}_{suf}_hd.json', 'w') as wr:
            wr.write(json.dumps(dict(r.headers), indent=4))
        if r.status_code != 204:
            with open(f'request_dump/{datepref}_{suf}_dt.json', 'w') as wr:
                wr.write(json.dumps(r.json(), indent=4))
    if req:
        with open(f'request_dump/{datepref}_{suf}_req.json', 'w') as wr:
            wr.write(json.dumps(req, indent=4))


# ------------------------------------------------------------------------------
def key_val_match(key: str, val: str | list[str], obj: Any) -> bool:
    """
    Return true if object at key matches val.

    We require a TRUE match on all (key, match_val) pairs in match

    :param key:     we match on the value of obj[key] key is . separated.
                    key=`a.b.c` means we match on `obj['a']['b']['c]`.
    :param val:     if plain string match directly. if list/tuple, match for any
                    item of val
    :param obj:     object we are matching value of obj[key]

    :return:        True if object at key matches val.

    """

    akey = key.split('.')
    objval = obj

    for k in akey:
        try:
            objval = objval[k]
        except (KeyError, TypeError):
            return False

    if isinstance(val, KeyExists):
        return True

    if val is None and objval is not None:
        return False

    # TODO: This logic fails if non-string/list/tuple values occur
    if isinstance(val, (list, tuple)):
        if objval not in val:
            return False
    elif isinstance(val, str):
        if objval != val:
            return False
    else:
        return False

    return True


# ------------------------------------------------------------------------------
def first_matching(data: list, match: Iterable[tuple[str, str]]) -> Any:
    """
    From a tuple or list of dicts return first item that matches all (key, match_val) criteria.

    We require a TRUE match on all (key, match_val) pairs in match
    Return the first matching entry

    :param data:    Python list we are searching for the first match
    :param match:   Iterable of ( (key, match_val), ... ) pairs
                    where match_val is list like then where the object value at
                    key matches one of match_val

    :return:        The located object or None if not found.
    :rtype:         T

    """

    obj = None
    found = True
    for o in data:
        for m in match:
            found = key_val_match(m[0], m[1], o)
            if not found:
                break
        if found:
            obj = o
            break
    return obj


# ------------------------------------------------------------------------------
def datetime_with_utc_tz() -> datetime.datetime:
    """
    Return the UTC time datetime set timezone UTC.

    To convert to a particular TZ use r_date.astimezone(dateutil.tz.gettz("Australia/Melbourne"))
    or as offset time r_date.astimezone(dateutil.tz.tzstr("GMT+11:00", posix_offset=False))

    :return:    Current date and time with UTC timezone
    """

    return datetime.datetime.now(datetime.timezone.utc)


# ------------------------------------------------------------------------------
def datetime_val(tv: str) -> datetime.datetime:
    """
    Set UTC for datetime without tzinfo.

    Uses dateutil parser.

    :param tv:  date

    :return:    datetime parsed result

    """

    tv = dateutil.parser.parse(tv)
    if tv.tzinfo is None:
        tv = tv.replace(tzinfo=dateutil.tz.UTC)
    return tv


# ------------------------------------------------------------------------------
def parse_http_retry_after(hd: dict) -> int:
    """
    Parse a HTTP Retry-After response header.

    Return number of seconds to wait. Default to 15 if Retry-Header doesn't
    exist or isn't integer number of seconds or (limited type) parsable date

    :param hd:  Headers from a http response (requests version)

    :return:        Number of seconds to wait

    """
    retry_time = 15
    try:
        retry_time = hd['Retry-After']
        try:
            return int(hd['Retry-After']) + 10
        except ValueError:
            retry_time = datetime_val(retry_time)
            retry_time = (retry_time - datetime_with_utc_tz()).total_seconds()
            retry_time = round(retry_time) + 10
    except KeyError:
        pass
    return retry_time


# ..............................................................................
# endregion Utilities
# ..............................................................................


# ------------------------------------------------------------------------------
class SharePointError(Exception):
    """Base class for other exceptions."""

    pass


# ------------------------------------------------------------------------------
class Sharepoint:
    """
    A SharePoint class.

    Obtains a valid token (immediately usable) using supplied credentials.

    :param org_base_url:    Base URL for the organisation's SharePoint.
    :param site_name:       SharePoint site name that we want to put content
    :param tenant:          Azure AD registered domain id
    :param client_id:       UUID of the Azure AD registered app under the registered
                            Domain (registration has Microsoft graph API
                            credentials)
    :param client_secret:   Credentials of the Azure AD registered app.
    :param user:            Delegated user credentials to access graph API.
    :param password:        Delegated user credentials
    :param https_proxy:     HTTPS proxy.
    :param logger:          For logging.

    """

    # --------------------------------------------------------------------------
    def __init__(
        self,
        org_base_url: str,
        site_name: str,
        tenant: str,
        client_id: str,
        client_secret: str,
        user: str,
        password: str,
        https_proxy: str = None,
        logger: logging.Logger = None,
    ):
        """Create a SharePoint instance."""

        self.__bearer_token = None
        self.__refresh_token = None
        self.__session = None
        self.__headers = None
        self.__site_id = None
        self.__proxies = {}
        self.__token_count = None
        self.__token_expiry = None
        self.__logger = logger if logger else NULL_LOGGER

        if not https_proxy:
            https_proxy = os.environ.get('HTTPS_PROXY')
        if https_proxy:
            self.__proxies['https'] = https_proxy

        self.__scope = (
            'sites.readwrite.all Files.ReadWrite.All user.read openid profile offline_access'
        )

        self.__token_header = {
            'Content-Type': 'application/x-www-form-urlencoded',
            'Accept': 'application/json',
            'User-Agent': FAKE_HTTP_USERAGENT,
        }

        self.__headers = {
            'Content-Type': 'application/json',
            'Accept': 'application/json',
            'Accept-Encoding': 'gzip, deflate',
            'Authorization': '',
            # Searched for consensus for MS Graph throttling is to fake a real
            # browser UserAgent. When done most users expressed far less
            # frequent occurrence of throttling
            'User-Agent': FAKE_HTTP_USERAGENT,
        }

        self.get_token(tenant, client_id, client_secret, user, password)

        self.__session = Session()

        # ----------------------------------------
        # Look up site ID by name
        url = f'{MS_GRAPH_API_URL}/sites/{org_base_url}:/sites/{site_name}'
        _throttled, res = self.graphapi_session_req(
            url, 'GET', f'Unable to find SharePoint site_name "{site_name}"'
        )
        self.__site_id = res['id']

    # --------------------------------------------------------------------------
    def get_token(
        self, tenant: str, client_id: str, client_secret: str, user: str, password: str
    ) -> None:
        """
        Get a OAUTH v2 Graph API Token (the client_id app) for delegated user.

        :param tenant:          Azure AD registered domain id
        :param client_id:       UUID of the Azure AD registered app under the
                                registered domain (registration has Microsoft
                                graph API credentials)
        :param client_secret:   Credentials of the Azure AD registered app.
        :param user:            Delegated user credentials to access graph API.
        :param password:        Delegated user credentials

        """

        self.__token_count = 1
        self.__token_expiry = datetime_with_utc_tz()
        token_url = f'{MS_LOGIN_URL}/{tenant}/oauth2/v2.0/token'

        token_payload = {
            'client_id': client_id,
            'client_secret': client_secret,
            'username': user,
            'password': password,
            'grant_type': 'password',
            'scope': self.__scope,
        }

        with post(
            token_url,
            headers=self.__token_header,
            data=token_payload,
            proxies=self.__proxies,
            timeout=API_TIMEOUT,
        ) as r:
            if r.status_code != 200:
                raise SharePointError(
                    f'Invalid logon credentials: Status {r.status_code} "{r.json()}"'
                )
            self.__bearer_token = r.json()

        if self.__bearer_token['token_type'] != 'Bearer':  # noqa: S105
            raise SharePointError('Invalid token_type returned. Needs to be "Bearer"')

        self.__headers['Authorization'] = (
            f'{self.__bearer_token["token_type"]} {self.__bearer_token["access_token"]}'
        )

        self.__refresh_token = {
            'client_id': client_id,
            'client_secret': client_secret,
            'refresh_token': self.__bearer_token['refresh_token'],
            'grant_type': 'refresh_token',
            'scope': self.__scope,
        }

        self.__token_expiry += datetime.timedelta(
            seconds=max(self.__bearer_token['expires_in'] - 300, 0)
        )

    # --------------------------------------------------------------------------
    def refresh_token(self) -> None:
        """Refresh an OAUTH v2 Graph API Token."""

        self.__token_count += 1
        self.__token_expiry = datetime_with_utc_tz()
        token_url = f'{MS_LOGIN_URL}/common/oauth2/v2.0/token'

        with post(
            token_url,
            headers=self.__token_header,
            data=self.__refresh_token,
            proxies=self.__proxies,
            timeout=API_TIMEOUT,
        ) as r:
            if r.status_code != 200:
                raise SharePointError(
                    f"Invalid logon credentials supplied: Status {r.status_code} '{r.json()}'"
                )
            self.__bearer_token = r.json()

        if self.__bearer_token['token_type'] != 'Bearer':  # noqa: S105
            raise SharePointError("Invalid token_type returned. Needs to be 'Bearer'")

        self.__headers['Authorization'] = (
            f"{self.__bearer_token['token_type']} {self.__bearer_token['access_token']}"
        )
        self.__refresh_token['refresh_token'] = self.__bearer_token['refresh_token']

        self.__token_expiry += datetime.timedelta(
            seconds=max(self.__bearer_token['expires_in'] - 300, 0)
        )

    # --------------------------------------------------------------------------
    def check_refresh_token(self) -> None:
        """
        Refresh an OAUTH v2 Graph API Token if it has expired.

        The number of refreshes is limited.

        """

        if (
            self.__token_expiry < datetime_with_utc_tz()
            and self.__token_count < TOKEN_COUNT_THRESHOLD
        ):
            self.refresh_token()

    # --------------------------------------------------------------------------
    def close(self) -> None:
        """
        Close the connection.

        For SharePoint this is a no-op but it should be called for consistency
        with other connectors as things may change in future.

        :rtype:     None.
        """

        pass

    # --------------------------------------------------------------------------
    def find_doc_library_drive_id(self, lib_name: str) -> str:
        """
        Find the drive_id of a SharePoint documentLibrary by lib_name.

        :param lib_name:    Sharepoint documentLibrary name to find.

        :return:            drive_id that was found.

        :raise SharePointError: If the upload fails.
        """

        # Get a list of drives from the SharePoint site
        url = f'{MS_GRAPH_API_URL}/sites/{self.__site_id}/drives'
        search = (
            ('driveType', 'documentLibrary'),
            ('name', lib_name),
        )
        return self.graphapi_iter_find_id(
            url, search, f'Unable to find SharePoint documentLibrary "{lib_name}"'
        )

    # --------------------------------------------------------------------------
    def find_list_id(self, list_name: str, list_type: str = 'only_generic') -> str:
        """
        Find the list_id of a SharePoint list by list_name.

        :param list_name:   Sharepoint list name to find.
        :param list_type:   list types to return.

        :return:            list_id that was found.

        :raise SharePointError: If the upload fails.
        """

        # Get list of SharePoint lists
        url = f'{MS_GRAPH_API_URL}/sites/{self.__site_id}/lists'

        list_search = ('genericList',)
        if list_type == 'include_tracking':
            list_search += ('issueTracking',)
        elif list_type == 'ANY':
            list_search = KeyExists()

        search = (
            ('name', list_name),
            ('list.template', list_search),
        )

        return self.graphapi_iter_find_id(
            url, search, f'Unable to find SharePoint list "{list_name}"'
        )

    # --------------------------------------------------------------------------
    def put_doc_no_upload_session(
        self, lib_name: str, path: str, src_file: str, title: str = None
    ) -> None:
        """
        Put a document into SharePoint documentLibrary lib_name.

        Delegated user requires write access to the documentLibrary.  AzureAD
        application required Graph API access `Sites.ReadWrite.All`.

        This uses a direct put to the sharepoint document. This is limited to
        documents <=4MB in size only. Requires upload session to larger files

        :param lib_name:    SharePoint documentLibrary name as found on the
                            SharePoint site (existence is verified).
        :param path:        Full path (filename included) to put the file.
        :param src_file:    Name of source file to put.
        :param title:       The Title metadata values to set in SharePoint

        :raise SharePointError: If the upload fails.
        :raise ValueError:  If bad parameters.

        """

        if not path.startswith('/'):
            raise ValueError(f'{path}: Absolute path required')

        if not 0 < os.path.getsize(src_file) <= MAX_DL_FILESIZE:
            raise SharePointError(f'{src_file}: File must be 1..{MAX_DL_FILESIZE} bytes')

        drive_id = self.find_doc_library_drive_id(lib_name)

        url = f'{MS_GRAPH_API_URL}/drives/{drive_id}/root:{path}:/content'

        item_id = None
        throttling_count = 0
        while throttling_count <= THROTTLING_LIMIT:
            with open(src_file, 'rb') as f:
                self.check_refresh_token()
                put_hd = dict(self.__headers)
                put_hd['Content-Type'] = 'application/octet-stream'
                req = Request('PUT', url, data=f, headers=put_hd)
                prepped = self.__session.prepare_request(req)
                with self.__session.send(prepped, proxies=self.__proxies, timeout=API_TIMEOUT) as r:
                    if r.status_code in (200, 201):
                        item_id = r.json()['id']
                        break
                    if r.status_code in RETRY_STATUS_CODES:
                        throttling_count += 1
                        # from the header we wait the number of seconds
                        # specified before calling in again
                        # we fail after THROTTLING_LIMIT throttled attempts
                        # dump_request("putdocthrottle", r)
                        wait_sec = parse_http_retry_after(r.headers)
                        if wait_sec > THROTTLING_MAX_DELAY:
                            raise SharePointError(
                                'Upload failed: MS Graph API Throttling delay was more than '
                                f'{THROTTLING_MAX_DELAY} seconds'
                            )
                        sleep(wait_sec)
                        continue
                    raise SharePointError(f'Upload failed: Status {r.status_code}: {r.json()}')

        if throttling_count == THROTTLING_LIMIT:
            raise SharePointError(
                f'Upload failed: MS Graph API Throttling limit of {THROTTLING_LIMIT} '
                'has been reached'
            )

        # If we have title we set the title field attribute
        if title:
            url = f'{MS_GRAPH_API_URL}/drives/{drive_id}/items/{item_id}/listitem/fields'
            self.graphapi_session_req(
                url, 'PATCH', 'Upload failed', data=json.dumps({'Title': title})
            )

    # --------------------------------------------------------------------------
    def delete_all_list_items(self, list_id: str, list_name: str) -> None:
        """
        Delete all items from a specified SharePoint list.

        Uses Microsoft Graph calls.

        :param list_id:     SharePoint List id
        :param list_name:   SharePoint Listname

        """

        url = f'{MS_GRAPH_API_URL}/sites/{self.__site_id}/lists/{list_id}/items'

        item_id_list = []

        while url:
            _throttled, res = self.graphapi_session_req(
                url, 'GET', f'Unable to list items on SharePoint list "{list_name}"'
            )

            for v in res['value']:
                item_id_list.append(v['id'])

            # handle pagination.
            url = res.get('@odata.nextLink')

        for item_id in item_id_list:
            url = f'{MS_GRAPH_API_URL}/sites/{self.__site_id}/lists/{list_id}/items/{item_id}'
            self.graphapi_session_req(
                url, 'DELETE', f'Unable to delete all items on SharePoint list "{list_name}"'
            )

    # --------------------------------------------------------------------------
    def get_doc(self, lib_name: str, path: str, out_file: str) -> str:
        """
        Get a document from SharePoint documentLibrary lib_name.

        Delegated user requires read access to the documentLibrary.  AzureAD
        application required Graph API access Sites.ReadWrite.All

        :param lib_name:    SharePoint documentLibrary name as found on the
                            SharePoint site (existence is verified).
        :param path:        full documentLibrary path (filename included) to
                            fetch. Must be abolute with leading /.
        :param out_file:    Name of file we will write data to.

        :return:            Title of the SharePoint document. Can be None if
                            the doc has no title.

        :raise SharePointError:  If the document doesn't exist or cannot be
                            downloaded.
        :raise ValueError:  If bad parameters.

        """

        if not path.startswith('/'):
            raise ValueError(f'{path}: Absolute path required')

        drive_id = self.find_doc_library_drive_id(lib_name)

        url = f'{MS_GRAPH_API_URL}/drives/{drive_id}/root:{path}'
        _throttled, res = self.graphapi_session_req(url, 'GET', 'Download failed')
        item_id = res['id']

        # Old version existed that used path
        # url = f'{MS_GRAPH_API_URL}/drives/{drive_id}/root:{path}:/content'
        self.get_doc_by_id(drive_id, item_id, out_file)

        # Obtain title field attribute
        url = f'{MS_GRAPH_API_URL}/drives/{drive_id}/items/{item_id}/listitem/fields'
        _throttled, res = self.graphapi_session_req(url, 'GET', 'Download failed')
        return res.get('Title')

    # --------------------------------------------------------------------------
    def get_doc_list_glob(self, doc_list: list[dict], out_path: str, glob: str = None) -> list[str]:
        """
        From doc_list download all files or all glob matched files to out_path directory.

        Enforce DOS style glob matching on the filename, i.e. case insensitive.

        :param doc_list:    List of documents in index 1 onwards to download to out_path.
        :param out_path:    directory to download sharepoint file to.
        :param glob:        glob pattern to match on.

        :return:            List of files downloaded.
        """

        drive_id = doc_list[0]['drive_id']

        if glob:
            glob = glob.lower()

        files = []

        for x in doc_list[1:]:
            fn = x['name'].lower()
            if not x['folder'] and (glob is None or fnmatchcase(fn, glob)):
                self.get_doc_by_id(drive_id, x['id'], os.path.join(out_path, x['name']))
                files.append(x['name'])

        return files

    # --------------------------------------------------------------------------
    def get_multi_doc(self, lib_name: str, path: str, out_path: str, glob: str = None) -> list[str]:
        """
        Get multiple documents from SharePoint documentLibrary lib_name and path.

        Delegated user requires read access to the documentLibrary.  AzureAD
        application required Graph API access Sites.ReadWrite.All

        :param lib_name:    SharePoint documentLibrary name as found on the
                            SharePoint site (existence is verified).
        :param path:        full documentLibrary path (filename included) to
                            fetch. Must be abolute with leading /.
        :param out_path:    Name of directory to write files too
        :param glob:        The search filename glob pattern to match and download files.
                            e.g. `*.csv` for all csv

        :return:            List of filenames downloaded from SharePoint folder.

        :raise SharePointError:  If the document doesn't exist or cannot be
                            downloaded.
        :raise ValueError:  If bad parameters.

        """

        files = []
        if not path.startswith('/'):
            raise ValueError(f'{path}: Absolute path required')

        drive_id = self.find_doc_library_drive_id(lib_name)

        if path != '/':
            path = path.rstrip('/')

        url = f'{MS_GRAPH_API_URL}/drives/{drive_id}/root'
        if path != '/':
            url = f'{url}:{path}'
        _throttled, res = self.graphapi_session_req(
            url, 'GET', f'Path "{path}" in Sharepoint documentLibrary "{lib_name}" does not exist'
        )
        item_id = res['id']
        if 'folder' not in res:
            raise SharePointError(
                f'Path "{path}" in Sharepoint documentLibrary "{lib_name}" is not a folder'
            )

        res = self.list_lib_by_id(drive_id, item_id)
        files.extend(self.get_doc_list_glob(res, out_path, glob))

        while res[0]['url']:
            res = self.iter_drive_children(
                res[0]['url'], f'Unable to list drive items with id "{drive_id}" and path "{path}"'
            )
            res[0].update({'drive_id': drive_id})
            files.extend(self.get_doc_list_glob(res, out_path, glob))

        return files

    # --------------------------------------------------------------------------
    def get_list(
        self,
        list_name: str,
        out_file: str,
        system_columns: str = None,
        data_columns: str = None,
        header: bool = True,
        **csv_writer_args,
    ) -> int:
        """
        Get a SharePoint List list_name and write as CSV file with header.

        Delegated user requires read access to the List. AzureAD application
        requires Graph API access Sites.ReadWrite.All

        :param list_name:       SharePoint List name as found on the SharePoint
                                site (existence is verified).
        :param out_file:        CSV out_file. Where to write the last as plain
                                text csv
        :param system_columns:  Comma separated list of identified system
                                columns to get in addition to data columns.
        :param data_columns:    Comma separated list of columns wanted in the
                                export (if system_columns has values they are in
                                the export even if not listed here).
        :param header:          If True, include a header line with column
                                names. Default True.
        :param csv_writer_args: All other keyword arguments are assumed to be
                                CSV format params as per csv.writer() and are
                                passed directly to the writer.

        :return:                The number of data rows exported
                                (including header).

        """

        # ID column needs to be specified as ID in select list.
        # But when it comes in fields data it's only ever lowercase.
        # Is this to conform to microsoft standards and features that everyone else knows as a bug?
        if system_columns:
            # split system_columns on ,. Enforce id column in any case to be value ID
            include_syscols = [
                x.strip() if x.strip() != 'id' else 'ID'
                for x in system_columns.lower().split(',')
                if x.strip()
            ]
            include_syscols = [
                x for i, x in enumerate(include_syscols) if include_syscols.index(x) == i
            ]
        else:
            include_syscols = []

        list_id = self.find_list_id(list_name, 'include_tracking')

        url = f'{MS_GRAPH_API_URL}/sites/{self.__site_id}/lists/{list_id}?$expand=columns'
        field_type = self.list_field_types(
            url, f"Unable to list items on SharePoint list '{list_name}'"
        )
        data_col_list = []
        if data_columns:
            data_col_list = [
                x.strip()
                for x in data_columns.lower().split(',')
                if x.strip() and x.strip() in field_type
            ]
            data_col_list = [x for i, x in enumerate(data_col_list) if data_col_list.index(x) == i]
            data_col_list = [
                x
                for x in data_col_list
                if field_type[x]['type'] == 'standard'
                and (
                    (x.endswith('lookupid') and field_type[x]['lookup'])
                    or (not x.endswith('lookupid'))
                )
            ]
        if not data_col_list:
            data_col_list = [
                x
                for x in field_type
                if field_type[x]['type'] == 'standard'
                and (
                    (x.endswith('lookupid') and field_type[x]['lookup'])
                    or (not x.endswith('lookupid'))
                )
            ]

        # Get the columns we need
        # csv_header_cols = [
        #     (field_type[x]['ix'], field_type[x]['orig'], field_type[x]['data_type'],)
        #                    for x in field_type
        #                    if (field_type[x]['type'] == "standard" and x in data_col_list)
        #                    or (field_type[x]['type'] in ("readonly", "hidden")
        #                        and x in [z.lower() for z in include_syscols])
        # ]
        csv_header_cols = list(data_col_list)
        csv_header_cols.extend(
            [
                x
                for x in include_syscols
                if (x in field_type and field_type[x]['type'] in ('readonly', 'hidden'))
                or x == 'ID'
            ]
        )
        csv_header_cols = [field_type[x]['actual'] if x != 'ID' else x for x in csv_header_cols]
        cols = ','.join(csv_header_cols)
        url = (
            f'{MS_GRAPH_API_URL}/sites/{self.__site_id}/lists/'
            f'{list_id}/items?$expand=fields($select={cols})'
        )

        row_count = 0

        with open(out_file, 'w', newline='', encoding='utf-8') as f:
            csvf = csv.writer(f, **csv_writer_args)

            if header:
                csvf.writerow(csv_header_cols)

            # fix for id column issue
            csv_header_cols = [col if col.lower() != 'id' else 'id' for col in csv_header_cols]

            while url:
                _throttled, res = self.graphapi_session_req(
                    url, 'GET', f'Unable to list items on SharePoint list "{list_name}"'
                )
                # if row_count == 0:
                #     throttled, res = self.graphapi_session_req(
                #           url, "GET",
                #           f"Unable to list items on SharePoint list '{list_name}'",
                #           dump_req="get_list")
                # else:
                #     throttled, res = self.graphapi_session_req(
                #           url, "GET",
                #           f"Unable to list items on SharePoint list '{list_name}'")
                rws = []

                for item in res['value']:
                    rws.append(
                        [
                            str(item['fields'].get(col, '')) if col.lower() != 'id' else item['id']
                            for col in csv_header_cols
                        ]
                    )
                    row_count += 1
                csvf.writerows(rws)

                # handle pagination.
                url = res.get('@odata.nextLink')

        return row_count + 1

    # --------------------------------------------------------------------------
    def graphapi_session_req(
        self,
        url: str,
        method: str,
        base_error: str,
        upd_header: dict[str, Any] = None,
        status_ok: list[int] = None,
        data: Any = None,
        dump_req: str = None,
    ) -> Any:
        """
        Call into MS Graph API session with a http request given in method.

        Raise errors on error responses Handle all requests and throttle
        properly.  Handle for ProxyError as though that was graph API hard
        throttling dropping a connection.

        :param url:         start url to iterate over
        :param method:      the HTTP method for this request
        :param base_error:  error string to show on error
        :param upd_header:  request headers to update with (replacing
                            existing session headers)
        :param status_ok:   list of http status values that aren't errors
        :param data:        data for the request if required
        :param dump_req:    file to dump the request_too (for debugging)

        :return:            payload

        :raise SharePointError: on any http error

        """
        if not status_ok:
            if method == 'GET':
                status_ok = (200,)
            elif method == 'DELETE':
                status_ok = (200, 204)
            elif method in ('PATCH', 'PUT', 'POST'):
                status_ok = (200, 201)
            else:
                status_ok = (200,)

        throttled = False
        throttling_count = 0
        while throttling_count <= THROTTLING_LIMIT:
            self.check_refresh_token()
            req_header = dict(self.__headers)
            if upd_header:
                req_header.update(upd_header)
            if method in ('POST', 'PUT', 'PATCH'):
                req = Request(method, url, headers=req_header, data=data)
            else:
                # GET, DELETE
                req = Request(method, url, headers=req_header)
            prepped = self.__session.prepare_request(req)
            try:
                with self.__session.send(prepped, proxies=self.__proxies, timeout=API_TIMEOUT) as r:
                    if dump_req:
                        if data:
                            dump_request(dump_req, r, json.loads(data))
                        else:
                            dump_request(dump_req, r)
                    if r.status_code in status_ok:
                        if r.status_code != 204:
                            return throttled, r.json()
                        return throttled, None

                    # if we delete or patch and item doesn't exist assume user
                    # called in with ID that's already deleted. Assume this is
                    # fine.  403 is access denied. I was getting these issues
                    # when an item was pending being deleted
                    # and was requested to delete again. Handling for that
                    if method in ('DELETE', 'PATCH') and r.status_code in (404, 403):
                        return throttled, None
                    # Office 365/SharePoint API/MS Graph API do throttling
                    # https://docs.microsoft.com/en-us/onedrive/developer/rest-api/concepts/scan-guidance?view=odsp-graph-online
                    # doc above specifies to actually wait the throttle time
                    # before calling in again Assuming that they mean per
                    # session token used as lava can run multiple jobs at one
                    # using the same  MS Graph application and under the same
                    # service account user
                    if r.status_code in RETRY_STATUS_CODES:
                        throttling_count += 1
                        throttled = True
                        # from the header we wait the number of seconds
                        # specified before calling in again we fail after
                        # THROTTLING_LIMIT throttled attempts
                        # dump_request("apigetthrottle", r)
                        wait_sec = parse_http_retry_after(r.headers)
                        wait_sec += throttling_count * THROTTLING_BACKOFF_SECONDS
                        self.__logger.warning(
                            f'SharePoint: Throttled for the {throttling_count} time '
                            f'and waiting {wait_sec} seconds. '
                            f'Status {r.status_code}. base_error: {base_error}'
                        )
                        if wait_sec > THROTTLING_MAX_DELAY:
                            raise SharePointError(
                                f'{base_error}: MS Graph API Throttling delay was more than '
                                f'{THROTTLING_MAX_DELAY} seconds'
                            )

                        sleep(wait_sec)
                        continue
                    if r.status_code not in status_ok:
                        raise SharePointError(f'{base_error}: Status {r.status_code}: {r.json()}')
            except (ProxyError, ConnectionError, ReadTimeout) as e:
                throttling_count += 1
                throttled = True
                # Proxy error. Returned zero response handling.  Probably MS
                # GRAPH API shutting down it's connection for even HARDER
                # throttling.  or perhaps internal proxy issue where a proxy can
                # only be open for some time (I'm pretty sure not) or we have
                # reached some data limit output
                wait_sec = GRAPH_API_HARD_ERROR_WAIT_SECONDS
                self.__logger.warning(
                    f'Sharepoint: Throttled for the {throttling_count} time '
                    f'and waiting {wait_sec} seconds. '
                    f'ProxyError({e}). base_error: {base_error}'
                )
                sleep(wait_sec)
        if throttling_count == THROTTLING_LIMIT:
            raise SharePointError(
                f'{base_error}: MS Graph API Throttling limit of {THROTTLING_LIMIT} '
                'has been reached'
            )

        # Should not get here
        return None

    # --------------------------------------------------------------------------
    def graphapi_iter_find_id(self, url: str, search: Iterable[tuple[str, str]], error: str) -> str:
        """
        Iterate over a MS Graph API list obtaining first id based on search tuple.

        :param url:   start url to iterate over
        :param search:   search criteria to find the first id of
        :param error:   error string to show on error

        :return:            id of first match

        :raise SharePointError: if id can't be found using error or when error
                                calling url next chain
        """

        find_id = None
        while url:
            _throttled, res = self.graphapi_session_req(url, 'GET', error)
            # handle pagination.
            url = res.get('@odata.nextLink')

            # Find target id wanted
            find_id = first_matching(res['value'], search)
            if find_id is not None:
                find_id = find_id['id']
                break

        if find_id is None:
            raise SharePointError(error)

        return find_id

    # --------------------------------------------------------------------------
    def put_list(
        self,
        list_name: str,
        src_file: str,
        mode: str = 'append',
        error_missing: bool = False,
        data_columns: str = None,
        **csv_reader_args,
    ) -> int:
        """
        Put a document into SharePoint List list_name.

        Delegated user requires write access to the List.  AzureAD application
        required Graph API access Sites.ReadWrite.All

        Uses MS Graph API batch to put 20 items on the list at once.

        :param list_name:   SharePoint List name as found on the SharePoint site
                            (existence is verified).
        :param src_file:    CSV src_file to put. Requirement is plain text csv
                            source file.
        :param mode:        Update mode -- append or replace
        :param error_missing:  If True produce error if column exists in data
                               and isn't in the list.  Otherwise just display
                               a warning.
        :param data_columns: Comma seperated list of columns that are to be
                            included in sharepoint list item update or create
        :param csv_reader_args: Additional params are passed to the CSV reader.

        :return:            The number of data rows uploaded.

        """

        if mode not in ('append', 'replace', 'update', 'delete'):
            raise ValueError(f'Invalid mode: {mode}')

        list_id = self.find_list_id(list_name)

        url = f'{MS_GRAPH_API_URL}/sites/{self.__site_id}/lists/{list_id}?$expand=columns'
        field_type = self.list_field_types(
            url, f'Unable to list items on SharePoint list "{list_name}"'
        )
        data_col_list = []
        # put list is different to get list. For lookup field types we can only
        # create data into this column by submitting to field named
        # {colname}LookupID
        if data_columns:
            data_col_list = [
                x.strip()
                for x in data_columns.lower().split(',')
                if x.strip()
                and x.strip() in field_type
                and field_type[x.strip()]['type'] == 'standard'
                and (
                    (x.strip().endswith('lookupid') and field_type[x.strip()]['lookup'])
                    or (not x.strip().endswith('lookupid') and not field_type[x.strip()]['lookup'])
                )
            ]
        if not data_col_list:
            data_col_list = [
                x
                for x in field_type
                if field_type[x]['type'] == 'standard'
                and (
                    (x.endswith('lookupid') and field_type[x]['lookup'])
                    or (not x.endswith('lookupid') and not field_type[x.strip()]['lookup'])
                )
            ]

        throttled_backoff_count = 0
        row_count = -1
        request_list = []
        with open(src_file, newline='', encoding='utf-8') as f:
            csvf = csv.reader(f, **csv_reader_args)
            header = next(csvf)
            # noinspection PyUnusedLocal
            id_col = -1
            with suppress(StopIteration):
                id_col = next(i for i, x in enumerate(header) if x.lower() == 'id')
            mheader = []
            for i, v in enumerate(header):
                src = v.lower()
                if src in field_type:
                    mheader.append(
                        (
                            field_type[src]['ix'],
                            i,
                            field_type[src]['actual'],
                            field_type[src]['type'],
                            v.lower(),
                            field_type[src]['data_type'],
                            src,
                        )
                    )
            mheader.sort()
            col_required = {
                x
                for x in field_type
                if field_type[x]['type'] == 'standard'
                and field_type[x]['required']
                and (
                    (x.endswith('lookupid') and field_type[x]['lookup'])
                    or (not x.endswith('lookupid'))
                )
            }

            missing_required = col_required.difference([v.lower() for v in header])
            if missing_required and mode in ('append', 'replace'):
                raise SharePointError(
                    f'Missing required column: {missing_required} must be present in header'
                )

            non_existing = [v for v in header if v.lower() not in field_type]
            if non_existing and error_missing:
                raise SharePointError(
                    f'Columns present in file but not in SharePoint list: {non_existing}'
                )
            # Ignore columns present in the list but not present in the source data file
            readonly_items = [v[2] for v in mheader if v[3] == 'readonly' and v[2].lower() != 'id']
            if readonly_items:
                # Ignore any read-only columns that we are trying to update.
                pass

            if mode == 'replace':
                self.delete_all_list_items_batch(list_id, list_name)

            if mode in ('update', 'delete') and id_col == -1:
                raise SharePointError(
                    f'Missing column: Mode {mode} requires ID column to be present in header'
                )
            for row_count, r in enumerate(csvf):
                if mode in ('append', 'replace'):
                    data = {
                        'id': str(row_count),
                        'method': 'POST',
                        'url': f'/sites/{self.__site_id}/lists/{list_id}/items',
                        'body': {'fields': {}},
                        'headers': {'Content-Type': 'application/json'},
                    }
                    for v in mheader:
                        if v[4] not in data_col_list:
                            continue
                        # lookup value is blank string. equivalent of null
                        # don't bring in at all when creating listitem
                        # may need to bring it in as Null if required field type
                        # if v[4].endswith("lookupid") and r[v[1]].strip() == "":
                        #     continue
                        # if v[5] in ("blankasnull",) and r[v[1]].strip() == "":
                        #     continue
                        dataval = r[v[1]]
                        if dataval.strip() == '':
                            # if field_type[v[6]]['required']:
                            #     dataval = None
                            # else:
                            #     continue
                            continue
                        if v[5] == 'boolean':
                            if dataval.strip().lower()[0] in ('0', 'n', 'f'):
                                dataval = False
                            elif dataval.strip().lower()[0] in ('1', 'y', 't'):
                                dataval = True
                        data['body']['fields'][v[2]] = dataval
                elif mode in ('delete',):
                    data = {
                        'id': str(row_count),
                        'method': 'DELETE',
                        'url': f'/sites/{self.__site_id}/lists/{list_id}/items/{r[id_col]}',
                    }
                elif mode in ('update',):
                    data = {
                        'id': str(row_count),
                        'method': 'PATCH',
                        'url': f'/sites/{self.__site_id}/lists/{list_id}/items/{r[id_col]}/fields',
                        'body': {},
                        'headers': {'Content-Type': 'application/json'},
                    }
                    for v in mheader:
                        if v[4] not in data_col_list:
                            continue
                        dataval = r[v[1]]
                        if dataval.strip() == '':
                            dataval = None
                        # if v[4].endswith("lookupid") and dataval.strip() == "":
                        #     dataval = None
                        # elif v[5] in ("blankasnull",) and dataval.strip() == "":
                        #     dataval = None
                        # lookup value is blank string. equivalent of null
                        # when updating item set it to json null
                        data['body'][v[2]] = dataval
                request_list.append(data)
                if len(request_list) == 20:
                    if throttled_backoff_count:
                        throttled_backoff_count -= 1
                        throttled, batch_errors = self.batch_call(
                            request_list,
                            f'Write to list {list_name} from source at row {row_count + 1}',
                            True,
                        )
                    else:
                        throttled, batch_errors = self.batch_call(
                            request_list,
                            f'Write to list {list_name} from source at row {row_count + 1}',
                        )
                    if throttled:
                        throttled_backoff_count = THROTTLING_BACKOFF_LIMIT
                    if batch_errors:
                        SharePointError(
                            f'Unable to write to list "{list_name}" as mode "{mode}". '
                            f'Batch errors: {batch_errors}'
                        )
                    request_list = []

        if request_list:
            throttled, batch_errors = self.batch_call(
                request_list, f'Write to list {list_name} at source row {row_count + 1}', True
            )
            if batch_errors:
                SharePointError(
                    f'Unable to write to list "{list_name}" as mode "{mode}". '
                    f'Batch errors: {batch_errors}'
                )

        return row_count + 1

    # --------------------------------------------------------------------------
    def _batch_call_old(
        self, request_list: list[dict], batch_error: str, individual_requests: bool = False
    ) -> tuple[bool, dict]:
        """
        POST as a batch request_list using Microsoft Graph batch calls.

        Uses MS Graph API batch POST. There can only be 20 items at once. The
        assumption is request_list has no more than that

        :param request_list:    The list of MS Graph API requests to post in the
                                batch
        :param batch_error:     On response error what message is to be raised
                                in the SharePointError
        :param individual_requests:   Process each item on the batch
                                individually, to handle throttling back-off

        :return:            Two values (bool, int): (1) If the batch was
                            throttled at any time so we can implement back-off
                            better and (2) the requests that processed with
                            errors that wouldn't reprocess.

        """
        url = f'{MS_GRAPH_API_URL}/$batch'
        batch_errors = {}
        batch_type = {
            x['id']: {'method': x['method'], 'ind': i, 'retry': 0}
            for i, x in enumerate(request_list)
        }
        post_list = list(request_list)
        # it may be far better that the payload is gzipped here so there far
        # less data transferred and network latency is far less of an issue.
        wait_sec = THROTTLING_BACKOFF_SECONDS
        throttling_count = 0
        while throttling_count <= THROTTLING_LIMIT:
            batch_len = len(post_list)
            batch_ok, batch_throttle, batch_ignore_thr, batch_err, batch_ignore_err = 0, 0, 0, 0, 0
            chk = None
            if individual_requests:
                if not batch_len:
                    break
                chk = post_list.pop()
                self.check_refresh_token()
                if chk['method'] in ('POST', 'PUT', 'PATCH'):
                    req = Request(
                        chk['method'],
                        f'{MS_GRAPH_API_URL}{chk["url"]}',
                        headers=self.__headers,
                        data=json.dumps(chk['body']),
                    )
                else:
                    req = Request(
                        chk['method'], f'{MS_GRAPH_API_URL}{chk["url"]}', headers=self.__headers
                    )
                prepped = self.__session.prepare_request(req)
            else:
                data = {'requests': post_list}
                self.check_refresh_token()
                req = Request('POST', url, headers=self.__headers, data=json.dumps(data))
                prepped = self.__session.prepare_request(req)
                post_list = []
                # print("BATCH SUBMITTING COUNT, batch_len, batch_ok, batch_throttle,"
                #       "batch_ignore_thr, batch_err, batch_ignore_err "
                #       f"{throttling_count}: {batch_len}, {batch_ok}, {batch_throttle}, "
                #       f"{batch_ignore_thr}, {batch_err}, {batch_ignore_err}")
            with self.__session.send(prepped, proxies=self.__proxies, timeout=API_TIMEOUT) as dr:
                # Graph API batch is really stupid. Stuff like Throttling in a request shouldn't
                # be in a batch. The full request should fail with throttling!
                # instead we get a 200/204 and an individual item is marked as throttled.
                if individual_requests:
                    if dr.status_code in (200, 201, 204):
                        continue
                    if dr.status_code in (404,) and chk['method'] in ('DELETE', 'PATCH'):
                        continue
                    if dr.status_code in RETRY_STATUS_CODES:
                        post_list.append(chk)
                        # throttled handling is below
                    else:
                        batch_err += 1
                        batch_type[chk['id']]['retry'] += 1
                        if batch_type[chk['id']]['retry'] <= API_RETRY_THRESHOLD:
                            post_list.append(chk)
                        else:
                            batch_errors[chk['id']] = {
                                'status': dr.status_code,
                                'error': f'{dr.json()}',
                            }
                elif dr.status_code in (200, 204):
                    for chk in dr.json()['responses']:
                        if chk['status'] in (200, 201, 204):
                            batch_ok += 1
                            continue
                        # if we are updating or deleting a non-existing item just skip the error
                        # User has provided the wrong ID
                        if chk['status'] in (404,) and batch_type[chk['id']]['method'] in (
                            'DELETE',
                            'PATCH',
                        ):
                            batch_ok += 1
                            batch_ignore_err += 1
                            continue
                        # When a sharepoint list (or document list) grows more
                        # than 5000 items a common response
                        # is 429 with body.error.code = activitylimitreached
                        # this is different from real throttling which likely gives
                        # body.error.code = toomanyrequests and has
                        # body.error.innerError.status/code set.
                        # we consider those activitylimitreached without
                        # body.error.innerError.status/code to be
                        # throttling of large list notification
                        # if (
                        #     chk['status'] in (429, )
                        #     and chk['body']['error'].get
                        #     ('code', 'toomanyrequests').lower() == 'activitylimitreached'
                        #     and chk['body']['error'].get('innerError', {}).get('status') is None
                        #     and chk['body']['error'].get('innerError', {}).get('code') is None
                        #     ):
                        #     batch_ok += 1
                        #     batch_ignore_thr += 1
                        #     continue
                        # This is a single item throttled in the request
                        # we want to retry these again after waiting throttle time
                        if chk['status'] in (429, 502, 503, 504, 509):
                            batch_throttle += 1
                            wait_sec_upd = parse_http_retry_after(chk['headers'])
                            if wait_sec_upd > wait_sec:
                                wait_sec = wait_sec_upd
                            post_list.append(request_list[batch_type[chk['id']]['ind']])
                            continue
                        batch_err += 1
                        batch_type[chk['id']]['retry'] += 1
                        if batch_type[chk['id']]['retry'] <= API_RETRY_THRESHOLD:
                            post_list.append(request_list[batch_type[chk['id']]['ind']])
                        else:
                            batch_errors[chk['id']] = {
                                'status': chk['status'],
                                'error': chk['body']['error'],
                            }
                    # print("BATCH PROCESSED COUNT, batch_len, batch_ok, batch_throttle, "
                    #       "batch_ignore_thr, batch_err,batch_ignore_err "
                    #       f"{throttling_count}: {batch_len}, {batch_ok}, {batch_throttle}, "
                    #       f"{batch_ignore_thr}, {batch_err}, {batch_ignore_err}")
                    if batch_len == batch_ok:
                        break
                    # dump_request("batchcalloneormoreissue", dr, data)
                # the entire batch call responds that it was throttled.
                # Assumption is that all items in the batch failed
                # probably never occurs and only single items in the batch fail
                if dr.status_code in RETRY_STATUS_CODES:
                    throttling_count += 1
                    # from the header we wait the number of seconds specified
                    # before calling in again
                    # we fail after THROTTLING_LIMIT throttled attempts
                    # dump_request("batchcallthrottle", dr, data)
                    wait_sec = parse_http_retry_after(dr.headers)
                    if wait_sec > THROTTLING_MAX_DELAY:
                        raise SharePointError(
                            'Upload failed: MS Graph API Throttling delay was more than '
                            f'{THROTTLING_MAX_DELAY} seconds'
                        )
                    sleep(wait_sec)
                    continue
                # if dr.status_code not in (200, 201, 204, 429, 503, 509,):
                #     raise SharePointError(f"{batch_error}: Status {dr.status_code}: {dr.json()}")
            if batch_throttle:
                throttling_count += 1
                individual_requests = True
                if wait_sec > THROTTLING_MAX_DELAY:
                    raise SharePointError(
                        'Upload failed: MS Graph API Throttling delay was more than '
                        f'{THROTTLING_MAX_DELAY} seconds'
                    )
                sleep(wait_sec)
            if batch_ignore_thr:
                wait_sec = THROTTLING_BACKOFF_SECONDS * 2
                sleep(wait_sec)
            if batch_err:
                wait_sec = THROTTLING_BACKOFF_SECONDS * 2
                sleep(wait_sec)
            if not individual_requests and not post_list:
                break

        if throttling_count == THROTTLING_LIMIT:
            raise SharePointError(
                f'{batch_error}: MS Graph API Throttling limit of {THROTTLING_LIMIT} '
                'has been reached'
            )

        if throttling_count:
            return True, batch_errors
        return False, batch_errors

    # --------------------------------------------------------------------------
    def batch_call(
        self, request_list: list[dict], batch_error: str, individual_requests: bool = False
    ) -> tuple[bool, dict]:
        """
        POST as a batch request_list using Microsoft Graph batch calls.

        Uses MS Graph API batch POST

        There can only be 20 items at once. The assumption is request_list has
        no more than 20 values.  Try hard to get the data in. If we have
        throttled issues we resort to single item inserts.  On http error types
        we reattempt up to API errors threashold before failing.

        :param request_list:    The list of MS Graph API requests to post in the
                                batch
        :param batch_error:     On response error what message is to be raised
                                in the SharePointError
        :param individual_requests:   Process each item on the batch
                                individually, to handle throttling back-off

        :return:            Two values (bool, int): (1) If the batch was
                            throttled at any time so we can implement back-off
                            better and (2) the requests that processed with
                            errors that wouldn't reprocess. This is currently an
                            empty dict as instead we hard fail with a raised
                            exception after trying hard to get data.

        """

        url = f'{MS_GRAPH_API_URL}/$batch'
        batch_errors = {}
        batch_type = {
            x['id']: {'method': x['method'], 'ind': i, 'retry': 0, 'status': '', 'error': ''}
            for i, x in enumerate(request_list)
        }
        post_list = list(request_list)
        throttling_count = 0

        wait_sec = THROTTLING_BACKOFF_SECONDS
        # it may be far better that the payload is gzipped here so there far
        # less data transferred and network latency is far less of an issue.
        while post_list:
            batch_len = len(post_list)
            batch_ok, batch_throttle, batch_ignore_thr, batch_err, batch_ignore_err = 0, 0, 0, 0, 0
            # print("BATCH SUBMITTING COUNT, batch_len, batch_ok, batch_throttle,"
            #       "batch_ignore_thr, batch_err, batch_ignore_err "
            #       f"{throttling_count}: {batch_len}, {batch_ok}, {batch_throttle}, "
            #       f"{batch_ignore_thr}, {batch_err}, {batch_ignore_err}", file=sys.stderr)
            if individual_requests:
                for chk in post_list:
                    iurl = f'{MS_GRAPH_API_URL}{chk["url"]}'
                    if chk['method'] in ('POST', 'PUT', 'PATCH'):
                        throttled, res = self.graphapi_session_req(
                            iurl, chk['method'], batch_error, data=json.dumps(chk['body'])
                        )
                        if throttled:
                            throttling_count += 1
                    else:
                        throttled, res = self.graphapi_session_req(iurl, chk['method'], batch_error)
                        if throttled:
                            throttling_count += 1
                # if there are errors they'll be raised otherwise batch_errors is an empty dict
                break

            data = {'requests': post_list}
            throttled, res = self.graphapi_session_req(
                url, 'POST', batch_error, data=json.dumps(data)
            )
            if throttled:
                throttling_count += 1
            post_list = []
            for chk in res['responses']:
                if chk['status'] in (200, 201, 204):
                    batch_ok += 1
                    continue
                # if we are updating or deleting a non-existing item just skip the error
                # User has provided the wrong ID
                # 404 is Not Found. i.e. item doesn't exist so has been delete
                # 403 is access denied. I was getting these issues when an item
                # was pending being deleted
                # and was requested to delete again. Handling for that
                if chk['status'] in (404, 403) and batch_type[chk['id']]['method'] in (
                    'DELETE',
                    'PATCH',
                ):
                    batch_ok += 1
                    batch_ignore_err += 1
                    continue
                if chk['status'] in (429, 502, 503, 504, 509):
                    throttling_count += 1
                    batch_throttle += 1
                    if 'headers' in chk:
                        wait_sec_upd = parse_http_retry_after(chk['headers'])
                    else:
                        wait_sec_upd = THROTTLING_BACKOFF_SECONDS
                    if wait_sec_upd > wait_sec:
                        wait_sec = wait_sec_upd
                    post_list.append(request_list[batch_type[chk['id']]['ind']])
                    continue
                batch_err += 1
                batch_type[chk['id']]['retry'] += 1
                self.__logger.warning(
                    f'Sharepoint: Unhandled batch error. batch_error: {batch_error}. '
                    f'item is: {chk}'
                )
                if batch_type[chk['id']]['retry'] <= API_RETRY_THRESHOLD:
                    batch_type[chk['id']]['status'] = chk['status']
                    batch_type[chk['id']]['error'] = chk['body']['error']
                    post_list.append(request_list[batch_type[chk['id']]['ind']])
                else:
                    batch_errors[chk['id']] = {
                        'status': chk['status'],
                        'error': chk['body']['error'],
                    }

            # print("BATCH PROCESSED COUNT, batch_len, batch_ok, batch_throttle, "
            #       "batch_ignore_thr, batch_err,batch_ignore_err "
            #       f"{throttling_count}: {batch_len}, {batch_ok}, {batch_throttle}, "
            #       f"{batch_ignore_thr}, {batch_err}, {batch_ignore_err}", file=sys.stderr)
            if batch_len == batch_ok:
                break
            if batch_throttle:
                # add additional seconds for each item throttled
                wait_sec += batch_throttle * THROTTLING_BACKOFF_SECONDS
                self.__logger.warning(
                    f'Sharepoint: Throttled for {batch_throttle} items '
                    f'in a batch of size {batch_len}. '
                    f'Wait seconds {wait_sec}. batch_error: {batch_error}.'
                )
                sleep(wait_sec)
                individual_requests = True
            if batch_ignore_thr:
                wait_sec = THROTTLING_BACKOFF_SECONDS * 2
                sleep(wait_sec)
            if batch_err:
                wait_sec = THROTTLING_BACKOFF_SECONDS * 2
                sleep(wait_sec)

        if throttling_count:
            return True, batch_errors

        return False, batch_errors

    # --------------------------------------------------------------------------
    def delete_all_list_items_batch(self, list_id: str, list_name: str) -> None:
        """
        Batch delete all items from a specified SharePoint list.

        Uses MS Graph API batch POST to delete a batch of 20 items at a time.

        :param list_id:     SharePoint List id
        :param list_name:   SharePoint Listname

        """

        throttled_backoff_count = 0
        url = f'{MS_GRAPH_API_URL}/sites/{self.__site_id}/lists/{list_id}/items'
        while True:
            throttled, res = self.graphapi_session_req(
                url, 'GET', f'Unable to list items on SharePoint list "{list_name}"'
            )
            items = [v['id'] for v in res['value']]
            if not items:
                break
            request_list = []
            for i, v in enumerate(items):
                request_list.append(
                    {
                        'id': str(i),
                        'method': 'DELETE',
                        'url': f'/sites/{self.__site_id}/lists/{list_id}/items/{v}',
                    }
                )
                # MS graph API batch can only handle 20 requests.
                # This wasn't documented anywhere @20190820 but from testing
                # when I put in 20 or fewer requests the
                # batch POST didn't respond with 400 error "batch too large"
                if len(request_list) == 20:
                    if throttled_backoff_count:
                        throttled_backoff_count -= 1
                        throttled, batch_errors = self.batch_call(
                            request_list,
                            f'Unable to delete all items on SharePoint list "{list_name}"',
                            True,
                        )
                    else:
                        throttled, batch_errors = self.batch_call(
                            request_list,
                            f'Unable to delete all items on SharePoint list "{list_name}"',
                        )
                    if throttled:
                        throttled_backoff_count = THROTTLING_BACKOFF_LIMIT
                    if batch_errors:
                        SharePointError(
                            'Unable to delete all items on SharePoint list '
                            f'"{list_name}" in batch. Batch Errors: {batch_errors}'
                        )
                    request_list = []

            if request_list:
                throttled, batch_errors = self.batch_call(
                    request_list, f'Unable to delete all items on SharePoint list "{list_name}"'
                )
                if throttled:
                    throttled_backoff_count = THROTTLING_BACKOFF_LIMIT
                if batch_errors:
                    SharePointError(
                        'Unable to delete all items on SharePoint list '
                        f'"{list_name}" in batch. Batch Errors: {batch_errors}'
                    )

    # --------------------------------------------------------------------------
    def list_field_types(self, url: str, base_error: str) -> dict[str, dict[str, Any]]:
        """
        Get the field types of the specified SharePoint fields.

        Iterates over the expanded fields MS Graph API call returning type of
        field it is Raise errors on error responses.

        :param url:         start url to iterate over
        :param base_error:  error string to show on error

        :return:            iterated fields types

        :raise SharePointError: on any http error

        """

        _throttled, res = self.graphapi_session_req(url, 'GET', base_error)
        # throttled, res = self.graphapi_session_req(url, "GET", base_error, dump_req="columnlist")
        # dump_request("list_expand_columns", None, res)

        # When a list is created many system/control columns are created.
        # This selects only the ones that were manually created. seems right
        # so far at least. The per column list payload is a dictionary. We use
        # "name" in data and front end SharePoint us shows DisplayName.
        # Attachments for a list entry is always ignored. readOnly fields are
        # considered system fields. For append, replace, update or a list pretty
        # much only type "standard" and "hidden" can be used
        field_type = {}
        for i, x in enumerate(res['columns']):
            col_name = x['name'].lower()
            ft = 'standard'
            if x.get('columnGroup', 'N') == '_Hidden' or x['name'] == 'Attachments':
                ft = 'ignore'
            elif x.get('readOnly', True):
                ft = 'readonly'
            elif x.get('hidden', True):
                ft = 'hidden'

            # assumed so far everything had been text fields.
            # handling now for personorgroup fields which required
            # POST/PATCH requests based on <name>LookupId
            # there probably more like general lookups which aren't yet
            # handled.
            # TODO: all column types that are to be blank can be provided as JSON null.
            # JSON null in text field type is the blank string.
            # required fields that are allowed to be blank can be created as JSON null value
            # or even not provided in the payload and assumed to be null
            # if we want to update a field with a value to empty the field must be provided in
            # PATCH request with null value
            eft = 'notype'
            for z in x:
                if isinstance(x[z], dict) and z.lower() not in ('defaultvalue',):
                    eft = z.lower()

            # eft = "blankasnull"
            # if "text" in x:
            #     eft = "text"
            #     if x['text']['allowMultipleLines']:
            #         eft = f"{eft}_multiline"
            # elif "personOrGroup" in x:
            #     eft = "personorgroup"
            #     if x['personOrGroup']['allowMultipleSelection']:
            #        eft = f"{eft}_multi"

            haslookup = False
            # need to add in the lookupid equivalent columns for personorgroup types
            if eft.startswith('personorgroup'):
                haslookup = True
            field_type[col_name] = {
                'type': ft,
                'ix': i,
                'orig': x['name'],
                'actual': x['name'],
                'data_type': eft,
                'required': x.get('required', False),
                'lookup': haslookup,
            }
            if haslookup:
                col_name = f'{col_name}lookupid'
                field_type[col_name] = {
                    'type': ft,
                    'ix': i,
                    'orig': x['name'],
                    'actual': f'{x["name"]}LookupId',
                    'data_type': eft,
                    'required': x.get('required', False),
                    'lookup': haslookup,
                }

        return field_type

    # --------------------------------------------------------------------------
    def get_doc_by_id(self, drive_id: str, item_id: str, out_file: str) -> None:
        """
        Get a document from SharePoint documentLibrary lib_name.

        For already known drive_id, item_id.  Write to out_file

        :param drive_id:    SharePoint documentLibrary Drive ID (obtained
                            previously)
        :param item_id:     id of file to download (obtained previously)
        :param out_file:    Name of file we will write data to.

        :raise SharePointError:  If the document doesn't exist or cannot be
                            downloaded.

        """

        url = f'{MS_GRAPH_API_URL}/drives/{drive_id}/items/{item_id}/content'

        throttling_count = 0
        while throttling_count <= THROTTLING_LIMIT:
            self.check_refresh_token()
            get_hd = dict(self.__headers)
            get_hd['Content-Type'] = 'application/octet-stream'
            get_hd['Accept'] = 'application/octet-stream'
            req = Request('GET', url, headers=get_hd)
            prepped = self.__session.prepare_request(req)
            with self.__session.send(
                prepped, proxies=self.__proxies, timeout=API_TIMEOUT, stream=True
            ) as r:
                if r.status_code in (200, 201):
                    with open(out_file, 'wb') as f:
                        for chunk in r.iter_content(chunk_size=8192):
                            if chunk:  # filter out keep-alive new chunks
                                f.write(chunk)
                    break
                if r.status_code in RETRY_STATUS_CODES:
                    throttling_count += 1
                    # from the header we wait the number of seconds specified
                    # before calling in again we fail after THROTTLING_LIMIT
                    # throttled attempts
                    # dump_request("getdocthrottle", r)
                    wait_sec = parse_http_retry_after(r.headers)
                    if wait_sec > THROTTLING_MAX_DELAY:
                        raise SharePointError(
                            'Download failed: MS Graph API Throttling delay was more than '
                            f'{THROTTLING_MAX_DELAY} seconds'
                        )
                    sleep(wait_sec)
                    continue
                raise SharePointError(f'Download failed: Status {r.status_code}: {r.json()}')
        if throttling_count == THROTTLING_LIMIT:
            raise SharePointError(
                f'Download failed: MS Graph API Throttling limit of {THROTTLING_LIMIT} '
                'has been reached'
            )

    # --------------------------------------------------------------------------
    def list_lib(self, lib_name: str, path: str) -> list[dict[str, Any]]:
        """
        List the contents of a SharePoint documentLibrary.

        Delegated user requires read access to the documentLibrary. AzureAD
        application required Graph API access Sites.ReadWrite.All

        :param lib_name:    SharePoint documentLibrary name as found on the
                            SharePoint site (existence is verified).
        :param path:        full documentLibrary path (filename included) to
                            fetch. Must be abolute with leading /.

        :return:            A list of entries.

                            TODO: It appears though that the first entry is the
                                  drive ID? Need to better explin the return info.

        :raise SharePointError:  If the document doesn't exist or cannot be
                            downloaded.

        """

        drive_id = self.find_doc_library_drive_id(lib_name)

        if path != '/':
            path = path.rstrip('/')
            url = f'{MS_GRAPH_API_URL}/drives/{drive_id}/root:{path}:/children'
        else:
            url = f'{MS_GRAPH_API_URL}/drives/{drive_id}/root/children'

        res = self.iter_drive_children(
            url, f'Unable to list drive items with id "{drive_id}" and path id "{path}"'
        )
        res[0].update({'drive_id': drive_id})
        return res

    # --------------------------------------------------------------------------
    def list_lib_by_id(self, drive_id: str, path_id: str) -> list[dict[str, Any]]:
        """
        List a documentLibrary folder using a known drive_id and path_id.

        :param drive_id:    The already found drive_id of the SharePoint documentLibrary
                            SharePoint site (existence is verified).
        :param path_id:     full documentLibrary path (filename included) to
                            fetch. Must be abolute with leading /.

        :return:            List of all elements.

        :raise SharePointError:  If error while listing.

        """

        url = f'{MS_GRAPH_API_URL}/drives/{drive_id}/items/{path_id}/children'
        res = self.iter_drive_children(
            url, f'Unable to list drive items with id "{drive_id}" and path "{path_id}"'
        )
        res[0].update({'drive_id': drive_id})
        return res

    # --------------------------------------------------------------------------
    def iter_drive_children(self, url: str, error: str) -> list[dict[str, Any]]:
        """
        Return a JSON list of items.

        Iterate over this returning a limited useful set of attributes we want.

        :param url:         The URL request we will get
        :param error:       If request rsponse with error what error to raise

        :return:            List of items with attributes we wanted.

        """

        _throttled, itemlist = self.graphapi_session_req(url, 'GET', error)
        res = [
            {'url': itemlist.get('@odata.nextLink')},
        ]

        for x in itemlist['value']:
            res.append(
                {
                    'name': x['name'],
                    'id': x['id'],
                    'size': x['size'],
                    'lastModifiedDateTime': x['lastModifiedDateTime'],
                    'modified_user_email': x['lastModifiedBy']['user']['email'],
                    'folder': 'folder' in x,
                }
            )
        return res

    # --------------------------------------------------------------------------
    def move_file(self, drive_id: str, file_id: str, path_id: str) -> None:
        """
        Move documentLibrary (drive_id) file specified by file_id to folder path_id.

        :param drive_id:    The already found drive_id of the sharepoint
                            documentLibrary SharePoint site (existence is
                            verified).
        :param file_id:     The already known file_id of the file within the
                            documentLibrary.
        :param path_id:     The already known path_id of a folder within the
                            documentLibrary to move the file to.

        :raise SharePointError:  If error while moving

        """

        url = f'{MS_GRAPH_API_URL}/drives/{drive_id}/items/{file_id}'

        # https://docs.microsoft.com/en-us/graph/api/resources/driveitem?view=graph-rest-1.0
        # "@microsoft.graph.conflictBehavior": "rename"
        # @microsoft.graph.conflictBehavior     string  The conflict resolution
        # behavior for actions that create a new item. You can use the values
        # fail, replace, or rename. The default for PUT is replace. An item
        # will never be returned with     this annotation. Write-only.
        # req = Request('GET', url, headers=get_hd)
        payload = {
            'parentReference': {'id': path_id},
            '@microsoft.graph.conflictBehavior': 'replace',
        }
        self.graphapi_session_req(
            url, 'PATCH', 'Folder reference update failed', data=json.dumps(payload)
        )

    # --------------------------------------------------------------------------
    def put_doc(self, lib_name: str, path: str, src_file: str, title: str = None) -> None:
        """
        Put a document into SharePoint documentLibrary lib_name.

        Delegated user requires write access to the documentLibrary.  AzureAD
        application required Graph API access Sites.ReadWrite.All Uses am upload
        session so can handle files > 4MB

        :param lib_name:    SharePoint documentLibrary name as found on the
                            SharePoint site (existence is verified).
        :param path:        Full path (filename included) to put the file.
        :param src_file:    Name of source file to put.
        :param title:       The Title metadata values to set in SharePoint

        :raise SharePointError: If the upload fails.
        :raise ValueError:  If bad parameters.

        """

        if not path.startswith('/'):
            raise ValueError(f'{path}: Absolute path required')

        file_size = os.path.getsize(src_file)

        drive_id = self.find_doc_library_drive_id(lib_name)

        url = f'{MS_GRAPH_API_URL}/drives/{drive_id}/root:{path}:/createUploadSession'

        upl_session = {'item': {'@microsoft.graph.conflictBehavior': 'replace'}}
        _throttled, upl_session_res = self.graphapi_session_req(
            url, 'POST', 'Upload failed', data=json.dumps(upl_session)
        )

        item_id = None
        put_hd = {'Content-Type': 'application/octet-stream', 'Accept': 'application/json'}
        data_st = 0
        with open(src_file, 'rb') as f:
            file_fragments_left = True
            while file_fragments_left:
                data = f.read(UPLOAD_SESSION_FRAGMENT_SIZE)
                if not data:
                    break
                data_sz = len(data)
                put_hd['Content-Length'] = f'{data_sz}'
                put_hd['Content-Range'] = f'bytes {data_st}-{data_st + data_sz - 1}/{file_size}'
                data_st += data_sz
                req = Request('PUT', upl_session_res['uploadUrl'], data=data, headers=put_hd)
                prepped = self.__session.prepare_request(req)
                throttling_count = 0
                while throttling_count <= THROTTLING_LIMIT:
                    with self.__session.send(
                        prepped, proxies=self.__proxies, timeout=API_TIMEOUT
                    ) as r:
                        # dump_request("putlargedoc", r)
                        if r.status_code in (202,):
                            break
                        if r.status_code in (
                            200,
                            201,
                        ):
                            # For last fragment of the upload session data MS Graph HTTP response
                            # status is 200/201 to represent the entire file is uploaded and the
                            # uploadSession is ended.
                            file_fragments_left = False
                            break
                        if r.status_code in RETRY_STATUS_CODES:
                            throttling_count += 1
                            wait_sec = parse_http_retry_after(r.headers)
                            if wait_sec > THROTTLING_MAX_DELAY:
                                raise SharePointError(
                                    'Upload failed: MS Graph API Throttling delay was more than '
                                    f'{THROTTLING_MAX_DELAY} seconds'
                                )
                            sleep(wait_sec)
                            continue
                        raise SharePointError(f'Upload failed: Status {r.status_code}: {r.json()}')
                else:
                    raise SharePointError(
                        f'Upload failed: MS Graph API Throttling limit of {THROTTLING_LIMIT} '
                        'has been reached'
                    )
            item_id = r.json()['id']

        # If we have title we set the title field attribute
        if title:
            url = f'{MS_GRAPH_API_URL}/drives/{drive_id}/items/{item_id}/listitem/fields'
            self.graphapi_session_req(
                url, 'PATCH', 'Upload failed', data=json.dumps({'Title': title})
            )

    # --------------------------------------------------------------------------
    def dump_col_list(self, list_name: str) -> None:
        """
        Dump the json response of a SharePoint list with column information.

        For debug only purpose. File is dumped as
        `YYYYMMDDHHMMSS.MSS_columnlist_dt.json` requires request_dump directory
        to exist

        :param list_name:   SharePoint list name as found on the SharePoint site
                            (existence is verified).

        """

        list_id = self.find_list_id(list_name)

        url = f'{MS_GRAPH_API_URL}/sites/{self.__site_id}/lists/{list_id}?$expand=columns'
        self.graphapi_session_req(url, 'GET', 'NO ERROR', dump_req='columnlist')
