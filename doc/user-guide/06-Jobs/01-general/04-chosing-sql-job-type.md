## Choosing an SQL Job Type

Lava provides the following SQL jobs types:

*   [sql](#job-type-sql)

*   [sqlc](#job-type-sqlc)

*   [sqli](#job-type-sqli)

*   [sqlv](#job-type-sqlv).

All of these will run blobs of SQL against a relational database using a lava
[database connector](#database-connectors) to connect to the
target database. Each job type has unique characteristics that make it more or
less suited for a given context.

The following table compares the job types as well as the stand-alone
[lava-sql](#lava-sql-utility) CLI utility:

| Feature                          | sql | sqli | sqlc | sqlv | lava-sql |
| -------------------------------- | :-: | :--: | :--: | :--: | :------: |
| Runs inside the lava worker      |  *  |  *   |      |      |          |
| Runs outside the lava worker     |     |      |  *   |  *   |     *    |
| Uniform, lava provided interface |  *  |  *   |      |  *   |     *    |
| DB specific client               |     |      |  *   |      |          |
| Timeout supported                |     |      |  *   |  *   |          |
| Can be killed on lava side       |     |      |  *   |  *   |     *    |
| SQL in-line in job-spec          |     |  *   |      |      |          |
| SQL in S3                        |  *  |      |  *   |  *   |          |
| Lava transaction support         |  *  |  *   |      |  *   |          |
| Jinja payload rendering          |  *  |  *   |  *   |  *   |          |
| Run multiple SQL statements      |  *  |  *   |  *   |  *   |     *    |
| Suitable for large jobs          |  *  |      |  **  |  **  |    **    |
| Lava CSV formatting control      |  *  |  *   |      |  *   |     *    |
| HTML output                      |     |      |  ?   |      |     *    |
| Output column headers            |  *  |  *   |  *   |  *   |     *    |
| Client side copy support         |     |      |  ?   |      |          |
| Runs as a stand-alone utility    |     |      |  *   |      |     *    |

`?` means support depends on database client capabilities.
