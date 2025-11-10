
    ## Connector type: mssql

The **mssql** connector handles connections to Microsoft SQL Server databases.


|Field|Type|Required|Description|
|-|-|-|-------------------------------------------------------------|
|conn\_id|String|Yes|Connection identifier.|
|description|String|No|Description.|
|database|String|Yes*|The name of the database within the database server.|
|driver|String|No|The ODBC driver specification. This must correspond to the name of a section in `/etc/odbcinst.ini`. The default is `FreeTDS`.|
|enabled|Boolean|Yes|Whether or not the connection is enabled.|
|host|String|Yes*|The database host DNS name or IP address.|
|password|String|Yes*|The name of an encrypted SSM parameter containing the password. For a given `<REALM>`, the SSM parameter name must be of the form `/lava/<REALM>/...` and the value must be a **secure string** encrypted using the `lava-<REALM>-sys` KMS key.|
|port|Number|Yes*|The database port number.|
|preserve\_case|Boolean|No|If `true`, don't fold database object names to lower case when quoting them for use in [db_from_s3](#job-type-db_from_s3) jobs. The default is `false` (i.e. case folding is enabled).|
|secret\_id|String|No|Obtain missing fields from AWS Secrets Manager. [More information](#database-authentication-using-aws-secrets-manager).|
|subtype|String|No|Specifies the underlying DBAPI 2.0 driver. The default and only allowed value is `pyodbc`.|
|timeout|Integer|No|Connection timeout in seconds. If not specified, no timeout is applied.|
|type|String|Yes|`mssql`.|
|user|String|Yes*|Database user name.|

!!! info
    Fields with a **Required** column marked with `*` can have a value provided
    directly in the connection specification or indirectly via AWS Secrets
    Manager using the `secret_id` field.  See [Database Authentication Using AWS
    Secrets Manager](#database-authentication-using-aws-secrets-manager) for
    more information.

SSL connections are not currently supported.

When used with [exe](#job-type-exe) and
[pkg](#job-type-pkg) job types, the connection is implemented by
the [lava-sql](#lava-sql-utility) CLI.

!!! note
    There are some MSSQL CLI tools that come with the TDS or unixODBC packages.
    None of them are wonderful so for now `lava-sql` will have to do. Also not
    wonderful but what do you expect for free?

### Implementation Notes

The current implementation requires the following components be installed and
configured on the lava worker:

*   [Free TDS](http://www.freetds.org/)

*   [unixODBC](http://www.unixodbc.org)

*   [pyodbc](https://pypi.org/project/pyodbc/)

[Configuring unixODBC with Free TDS](http://www.unixodbc.org/doc/FreeTDS.html)
