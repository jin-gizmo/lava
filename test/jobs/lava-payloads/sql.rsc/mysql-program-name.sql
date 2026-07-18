-- Query for program name (aka application_name in lava and Postgres).
-- Requires the Performance Schema to be enabled.

SELECT session_account_connect_attrs.ATTR_VALUE AS program_name,
       processlist.id,
       processlist.user,
       processlist.host,
       processlist.db,
       processlist.command,
       processlist.time,
       processlist.state,
       left(processlist.info, 30)
FROM information_schema.processlist
         LEFT JOIN performance_schema.session_account_connect_attrs ON (
            processlist.ID = session_account_connect_attrs.PROCESSLIST_ID
        AND session_account_connect_attrs.ATTR_NAME = "program_name"
    )
WHERE processlist.user <> 'rdsadmin';
