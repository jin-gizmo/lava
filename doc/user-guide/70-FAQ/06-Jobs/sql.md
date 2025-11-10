
### [sql](#job-type-sql)

#### Error: need to escape, but no escapechar set

When lava collects the output of a query from an
[sql](#job-type-sql) job, it uses the standard Python CSV
writer to format the data for output. If it detects that the data requires an
escape character to be specified but this has not been done in the job
specification, this error will result.
