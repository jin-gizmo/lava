
## SQL Jobs

The [sql](#job-type-sql),
[sqlc](#job-type-sqlc),
[sqli](#job-type-sqli) and
[sqlv](#job-type-sqlv) jobs will run SQL commands against a
target RDBMS.

There is nothing special that needs to be done with the SQL to prepare it to run
with lava but it is important to keep the following in mind:

*   Lava will manage all of the connectivity to the database.

*   The SQL must match the syntax requirements of the target database.

*   [sqlc](#job-type-sqlc) jobs use the command line client
    specific to the target database. Typically these will support some client
    specific meta commands to control behaviour of the client. These can be used
    in the job payload script.

*   [sqlc](#job-type-sqlc) and
    [sqlv](#job-type-sqlv) jobs have a timeout that can be
    configured in the job specification. [sql](#job-type-sql)
    and [sqli](#job-type-sqli) jobs do not have a timeout. Like
    all jobs, the visibility timeout on the worker queue needs to be kept in
    mind.

*   If the queries return data, this will be placed into the temporary area in
    S3. Some other process may need to do something with this data.
