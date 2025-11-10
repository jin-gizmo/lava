
## Connector type: smb

The **smb** connector manages connections to SMB file shares.

!!! info
    The **smb** connector has undergone a significant upgrade in v8.0
    (Incahuasi) to support the
    [smbprotocol](https://github.com/jborean93/smbprotocol) SMB implementation
    as well as the existing
    [pysmb](https://pysmb.readthedocs.io/en/latest/api/smb_SMBConnection.html).
    The former has a number of advantages (e.g. DFS support). An effort has been
    made to retain backward compatibility for lava jobs, notwithstanding the two
    implementations have significant interface differences. Be warned, though,
    that some more esoteric usage patterns could experience a backward
    compatibility issue.

|Field|Type|Required|Description|
|-|-|-|-------------------------------------------------------------|
|conn\_id|String|Yes|Connection identifier.|
|description|String|No|Description.|
|domain|String|No|The network domain. Defaults to an empty string.|
|enabled|Boolean|Yes|Whether or not the connection is enabled.|
|encrypt|Boolean|No|Whether to encrypt the connection between Lava and the SMB server. Only available with the `smbprotocol` connection subtype. Default `false`.|
|host|String|Yes|DNS name or IP address of the SMB host.|
|is\_direct\_tcp|Boolean|No|If `false`, use NetBIOS over TCP/IP. If `true` use SMB over TCP/IP. Default `false`.|
|my\_name|String|No|Local NetBIOS machine name that will identify the origin of connections. If not specified, defaults to the first 15 characters of `lava-<REALM>`|
|password|String|Yes|Name of the SSM parameter containing the password for authenticating to the SMB server. For a given `<REALM>`, the SSM parameter name must be of the form `/lava/<REALM>/...` and the value must be a secure string encrypted using the `lava-<REALM>-sys` KMS key.|
|port|Integer|No|Connection port number. If not specified, 139 is used if `is_direct_tcp` is `false` and 445 otherwise.|
|remote\_name|String|Yes|NetBIOS machine name of the remote server.|
|subtype|String|No|Which connection type to use, `smbprotocol` or the default `pysmb`. To use encryption or DFS for the connection use the `smbprotocol` subtype.|
|type|String|Yes|`smb`.|
|use\_ntlm\_v2|Boolean|No|Indicates whether pysmb should be NTLMv1 or NTLMv2 authentication algorithm for authentication. Default is `true`.|
|user|String|Yes|User name for authenticating to the SMB server.|

The connector supports the [smb_get](#job-type-smb_get) and
[smb_put](#job-type-smb_put) job types.

### Use with Python-based Executable Jobs { data-toc-label="Use with Python-based Jobs" }

The connector can also be used with Python based
[exe](#job-type-exe) and [pkg](#job-type-pkg)
jobs that invoke the lava connection manager directly. In this case, the
connector returns a `lava.lib.smb.LavaSMBConnection` which provides a basic,
common interface to the different subtypes.

The `lava.lib.smb.LavaSMBConnection` interface class provides enough
functionality for most common use-cases (list path, put file, get file etc.).

The concrete implementation is handled by of one of two subclasses (depending on
the `subtype` given in the connection spec):

-   a `lava.lib.smb.PySMBConnection` which implements `LavaSMBConnection` using
    the Python package
    [pysmb](https://pysmb.readthedocs.io/en/latest/api/smb_SMBConnection.html).
    This is the **default** if no connection `subtype` is given.

-   a `lava.lib.smb.SMBProtocolConnection` which implements `LavaSMBConnection`
    using the Python package
    [smbprotocol](https://github.com/jborean93/smbprotocol).


Note that this is the low level connector. It does not handle moving files in or
out of S3 or Jinja rendering of parameters. It is up to the caller to do that as
required.

If the SMB connector key in the job's `connectors` map is `fserver`, typical
usage would be something like:

```python
import os
from lava.connection import get_smb_connection

# Get an smb.SMBConnection.SMBConnection instance
smb_conn = get_smb_connection(
    conn_id=os.environ['LAVA_CONNID_FSERVER'],
    realm=os.environ['LAVA_REALM']
)

# Get a file from share 'Public' and store locally
with open('local.txt', 'wb') as fp:
    attributes, size = smb_conn.retrieve_file('Public', 'some_file.txt', fp)

smb_conn.close()
```

### Use with Other Executable Jobs

When used with other [exe](#job-type-exe) and
[pkg](#job-type-pkg) job types (e.g. shell scripts), the
connection is implemented by the `lava-smb` command.

This is a somewhat higher level interface to the connector in that it can also
handle moving data in and out of S3. Jinja rendering is handled as per the
[smb_get](#job-type-smb_get) and
[smb_put](#job-type-smb_put) job types.

If the SMB connector key in the job's `connectors` map is `fserver`, usage is:

```bare
usage: $LAVA_CONN_FSERVER [-J] [-l LEVEL] {put,get} ...

sub-commands:
  {put,get}
    put                 Copy a file to an SMB file share.
    get                 Copy a file from an SMB file share.

optional arguments:
  -J, --no-jinja        Disable Jinja rendering of the transfer parameters.

logging arguments:
  -l LEVEL, --level LEVEL
                        Print messages of a given severity level or above. The
                        standard logging level names are available but debug,
                        info, warning and error are most useful. The Default
                        is info.
```


Usage for the `get` sub-command:

```bare
usage: $LAVA_CONN_FSERVER get [options] SMB-path file

positional arguments:
  SMB-path              Source location. Must be in the form share-name:path.
                        This will be jinja rendered.
  file                  Target file. Values starting with s3:// will be copied
                        to S3. This will be jinja rendered.

optional arguments:
  -k KMS_KEY_ID, --kms-key-id KMS_KEY_ID
                        AWS KMS key to use for uploading data to S3.
```

Usage for the `put` sub-command:

```bare
usage: $LAVA_CONN_FSERVER put [options] file SMB-path

positional arguments:
  file         Source file. Values starting with s3:// will be copied from S3.
               This will be jinja rendered.
  SMB-path     Target location. Must be in the form share-name:path. This will
               be jinja rendered.

optional arguments:
  -m, --mkdir  Create the target directory if it doesn't exist
```

For example, the following code in an [exe](#job-type-exe)
job would transfer files between S3 and the `Public` share on an SMB server:

```bash
#!/bin/bash

# Copy file from S3 to SMB
$LAVA_CONN_FSERVER put --mkdir \
    s3://my-bucket/data.csv Public:/a/path/data.csv

# Copy file from SMB to S3
$LAVA_CONN_FSERVER get --kms-key-id alias/data \
    Public:/a/path/data.csv s3://my-bucket/data.csv
```
