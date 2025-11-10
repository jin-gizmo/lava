
## Job Families

Jobs types can be roughly grouped into the following families.

*   **Orchestration jobs** that control the operation of other jobs:
    *   [chain](#job-type-chain)
    *   [dag](#job-type-dag)
    *   [dispatch](#job-type-dispatch)
    *   [foreach](#job-type-foreach)

*   **Database jobs** that interact with a database to run SQL or load / unload
    data:
    *   [db_from_s3](#job-type-db_from_s3)
    *   [redshift_unload](#job-type-redshift_unload)
    *   [sql](#job-type-sql)
    *   [sqlc](#job-type-sqlc)
    *   [sqli](#job-type-sqli)
    *   [sqlv](#job-type-sqlv)

    See also [Choosing an SQL Job Type](#choosing-an-sql-job-type).

*   **Executable jobs** that run a code bundle external to lava itself:
    *   [cmd](#job-type-cmd)
    *   [docker](#job-type-docker)
    *   [exe](#job-type-exe)
    *   [pkg](#job-type-pkg)

*   **Integration jobs** that interact with an external system of some kind:
    *   [sharepoint_get_doc](#job-type-sharepoint_get_doc)
    *   [sharepoint_get_list](#job-type-sharepoint_get_list)
    *   [sharepoint_get_multi_doc](#job-type-sharepoint_get_multi_doc)
    *   [sharepoint_put_doc](#job-type-sharepoint_put_doc)
    *   [sharepoint_put_list](#job-type-sharepoint_put_list)
    *   [smb_get](#job-type-smb_get)
    *   [smb_put](#job-type-smb_put)

*   **Lava internal jobs** that lava uses for it's own operations:
    *   [lavasched](#job-type-lavasched)

*   **Miscellaneous jobs** that don't fit the above:
    *   [log](#job-type-log)
