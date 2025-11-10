
### db_from_s3

#### Error: invalid byte sequence for encoding “UTF8”

This typically means either:

1.  The source data contains non-UTF8 characters; or

2.  The source is actually a gzip file but the `GZIP` option has not been
    specified in the job parameters.

#### Error: HTTP 412. The file has been modified since the import call started

This is probably the result of an S3 race condition. It shouldn't happen. Report
it if it does.
