
## Connector type: sqlite3

The **sqlite3** connector handles connections to SQLite3 file based databases.

Its use in general lava jobs is pretty marginal at best. It is mostly present to
facilitate testing of lava itself.

|Field|Type|Required|Description|
|-|-|-|-------------------------------------------------------------|
|conn\_id|String|Yes|Connection identifier.|
|description|String|No|Description.|
|enabled|Boolean|Yes|Whether or not the connection is enabled.|
|host|String|Yes|The name of the file containing the SQLite3 database. If it starts with `s3://`, the file will be copied from S3 when the connection is created and returned to S3 when the connection is closed if it has been modified.|
|port|Number|Yes*|A value is required but is ignored. 
|preserve\_case|Boolean|No|If `true`, don't fold database object names to lower case when quoting them for use in [db_from_s3](#job-type-db_from_s3) jobs. The default is `false` (i.e. case folding is enabled).|
|type|String|Yes|`sqlite3`.|
|user|String|Yes*|A value is required but is ignored.|

!!! info
    Fields with a **Required** column marked with `*` must be present but the
    value is ignored. This is an unfortunate interface idiosyncrasy resulting
    from the need to maintain some internal compatibility with the other
    database connectors.

When used with [exe](#job-type-exe) and
[pkg](#job-type-pkg) job types, the connection is implemented by
the `sqlite3` CLI.  It is invoked with the following options:

```bash
sqlite3 -bail -batch DATABASE-FILE
```
