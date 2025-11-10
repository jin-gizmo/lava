
## Connector type: sharepoint

The **sharepoint** connector manages connections to SharePoint sites.

It is possible for Microsoft to have made this process more complex and
unwieldy, but it is not obvious how.

|Field|Type|Required|Description|
|-|-|-|-------------------------------------------------------------|
|client\_id|String|Yes|The Application ID that the SharePoint registration portal assigned your app. This resembles a UUID.|
|client\_secret|String|Yes|Name of the SSE parameter containing the client secret. For a given `<REALM>`, the SSM parameter name must be of the form `/lava/<REALM>/...` and the value must be a secure string encrypted using the `lava-<REALM>-sys` KMS key.|
|conn\_id|String|Yes|Connection identifier.|
|description|String|No|Description.|
|enabled|Boolean|Yes|Whether or not the connection is enabled.|
|https\_proxy|String|No|HTTPS proxy to use for accessing the SharePoint API endpoints. If not specified, the `HTTPS_PROXY` environment variable is used, if set.|
|org\_base\_url|String|Yes|The hostname component of the organisation's SharePoint base URL. e.g. `acme.sharepoint.com`.|
|password|String|Yes|Name of the SSM parameter containing the password for authenticating to SharePoint. For a given `<REALM>`, the SSM parameter name must be of the form `/lava/<REALM>/...` and the value must be a secure string encrypted using the `lava-<REALM>-sys` KMS key.|
|site\_name|String|Yes|The SharePoint site name.|
|tenant|String|Yes|The Azure AD registered domain ID. This resembles a UUID.|
|type|String|Yes|`sharepoint`.|
|user|String|No|User name for authenticating to SharePoint.|

The connector supports the
[sharepoint_get_doc](#job-type-sharepoint_get_doc),
[sharepoint_get_list](#job-type-sharepoint_get_list),
[sharepoint_put_doc](#job-type-sharepoint_put_doc),
[sharepoint_put_list](#job-type-sharepoint_put_list) and
[sharepoint_get_multi_doc](#job-type-sharepoint_get_multi_doc) and
job types.

### Using SharePoint Connectors

The `sharepoint` connector provides two distinct interfaces:

1.  A [native Python interface](#python-interface-for-sharepoint-connectors)

2.  A [command line interface](#executable-interface-for-sharepoint-connectors).

#### Python Interface for SharePoint Connectors

The sharepoint connector can be used with Python based
[exe](#job-type-exe) and [pkg](#job-type-pkg)
jobs that invoke the lava connection manager directly. In this case, the
connector returns a `lava.lib.sharepoint.Sharepoint` object as described in the
lava API documentation. In summary, this class has the following methods:

```python
delete_all_list_items(list_id, list_name)

get_doc(lib_name, path, out_file)

get_list(list_name, out_file, system_columns=None, data_columns=None,
    header=True, **csv_writer_args)

put_doc(lib_name, path, src_file, title=None)

put_list(list_name, src_file, mode='append', error_missing=False,
    data_columns=None, **csv_reader_args)

get_multi_doc(lib_name, path, out_path, glob=None)

close()
```
Note that this is the low level connector. It does not handle moving files in or
out of S3 or Jinja rendering of parameters. It is up to the caller to do that as
required.

If the SharePoint connector key in the job's `connectors` map is `spoint`,
typical usage would be something like:

```python
import os
from lava.connection import get_sharepoint_connection

# Get a lava.lib.sharepoint.Sharepoint instance
sp_conn = get_sharepoint_connection(
    conn_id=os.environ['LAVA_CONNID_SPOINT'],
    realm=os.environ['LAVA_REALM']
)

# Get a list from SharePoint and store it locally.
row_count = sp_conn.get_list('postcodes', 'postcodes.csv', delimiter=',')

# Close the connection
sp_conn.close()
```

#### Executable Interface for SharePoint Connectors

When used with [exe](#job-type-exe),
[pkg](#job-type-pkg) and
[docker](#job-type-docker) job types (e.g. shell scripts), the
connection is implemented by the `lava-sharepoint` command.

This is a somewhat higher level interface to the connector in that it can also
handle moving data in and out of S3. Jinja rendering is handled as per the
[sharepoint_get_list](#job-type-sharepoint_get_list),
[sharepoint_put_list](#job-type-sharepoint_put_list),
[sharepoint_get_doc](#job-type-sharepoint_get_doc),
[sharepoint_put_doc](#job-type-sharepoint_put_doc) and
[sharepoint_get_multi_doc](#job-type-sharepoint_get_multi_doc)
job types.

If the SharePoint connector key in the job's `connectors` map is `spoint`,
usage is:

```bare
usage: $LAVA_CONN_SPOINT [-J] [-l LEVEL] {put-doc,put-list,get-doc,get-list,get-multi-doc} ...

sub-commands:
  {put-doc,put-list,get-doc,get-list,get-multi-doc}
    put-doc             Copy a file into a SharePoint document library.
    put-list            Copy a file into a SharePoint list.
    get-doc             Copy a file from a SharePoint document library.
    get-list            Copy a SharePoint list to a file
    get-multi-doc       Copy multiple files from a SharePoint document library path.

optional arguments:
  -J, --no-jinja        Disable Jinja rendering of the transfer parameters.

logging arguments:
  -l LEVEL, --level LEVEL
                        Print messages of a given severity level or above. The
                        standard logging level names are available but debug,
                        info, warning and error are most useful. The Default
                        is info.
```

Usage for the `get-doc` sub-command:

```bare
usage: $LAVA_CONN_SPOINT get-doc [options] SharePoint-path file

positional arguments:
  SharePoint-path       Source location. Must be in the form library:path.
                        This will be jinja rendered.
  file                  Target file. Values starting with s3:// will be copied
                        to S3. This will be jinja rendered.

optional arguments:
  -k KMS_KEY_ID, --kms-key-id KMS_KEY_ID
                        AWS KMS key to use for uploading data to S3.
```

Usage for the `get-list` sub-command:

```bare
usage: $LAVA_CONN_SPOINT get-list [options] SharePoint-list file

positional arguments:
  SharePoint-list       Source SharePoint list name. This will be jinja
                        rendered.
  file                  Target file. Values starting with s3:// will be copied
                        to S3. This will be jinja rendered.

optional arguments:
  -k KMS_KEY_ID, --kms-key-id KMS_KEY_ID
                        AWS KMS key to use for uploading data to S3.
  -H, --no-header       Don't include a header row. A header is included by
                        default.
  --delimiter DELIMITER
                        Output field delimiter.
  --double-quote        As for csv.writer.
  --escape-char ESCAPECHAR
                        As for csv.writer.
  --quote-char QUOTECHAR
                        As for csv.writer.
  --quoting QUOTING     As for csv.writer QUOTE_ parameters (without the
                        QUOTE_ prefix).
```

Usage for the `get-doc` sub-command:

```bare
usage: $LAVA_CONN_SPOINT get-doc [options] SharePoint-path file

positional arguments:
  SharePoint-path       Source location. Must be in the form library:path.
                        This will be jinja rendered.
  file                  Target file. Values starting with s3:// will be copied
                        to S3. This will be jinja rendered.

optional arguments:
  -k KMS_KEY_ID, --kms-key-id KMS_KEY_ID
                        AWS KMS key to use for uploading data to S3.
```

Usage for the `put-doc` sub-command:

```bare
usage: $LAVA_CONN_SPOINT put-doc [options] file SharePoint-path

positional arguments:
  file                  Source file. Values starting with s3:// will be copied
                        from S3. This will be jinja rendered.
  SharePoint-path       Target location. Must be in the form library:path.
                        This will be jinja rendered.

optional arguments:
  -t TITLE, --title TITLE
                        Document title. This will be jinja rendered.
```

Usage for the `get-multi-doc` sub-command:

```bare
usage: $LAVA_CONN_SPOINT get-multi-doc [options] SharePoint-path outpath [glob]

positional arguments:
  SharePoint-path       Source location. Must be in the form library:path.
                        This will be jinja rendered.
  outpath               Target path. Values starting with s3:// will be copied
                        to S3 using given bucket and key as key prefix. This
                        will be jinja rendered.
  glob                  Filter files in sharepoint path on this given glob.
                        This will be jinja rendered.

optional arguments:
  -k KMS_KEY_ID, --kms-key-id KMS_KEY_ID
                        AWS KMS key to use for uploading data to S3.
```

The following examples show how to use the connector in an
[exe](#job-type-exe) job using bash:

```bash
#!/bin/bash

# Copy a list from S3 to SharePoint, replacing existing contents.
$LAVA_CONN_SPOINT put-list --replace s3://my-bucket/data.csv My-List

# Get list back from SharePoint and place in S3. Include a header
$LAVA_CONN_SPOINT get-list -k alias/data --delimiter "," \
    My-List s3://my-bucket/data.csv

# Copy a document from S3 to SharePoint.
$LAVA_CONN_SPOINT put-doc s3://my-bucket/lava.docx "Lava Docs:/Lava/User Guide.docx"

# Get a document from SharePoint and place in S3.
$LAVA_CONN_SPOINT get-doc "Lava Docs:/Lava/User Guide.docx" s3://my-bucket/lava.docx 

# Get all docx files from SharePoint path and place in S3 base-prefix.
$LAVA_CONN_SPOINT get-multi-doc "Lava Docs:/Lava/" s3://my-bucket/base-prefix *.docx

# Get all files from SharePoint path and place in S3 base-prefix.
$LAVA_CONN_SPOINT get-multi-doc "Lava Docs:/Lava/" s3://my-bucket/base-prefix

```
