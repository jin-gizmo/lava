SELECT session_connect_attrs.ATTR_VALUE AS program_name,
       processlist.*
FROM information_schema.processlist
         LEFT JOIN performance_schema.session_connect_attrs ON (
            processlist.ID = session_connect_attrs.PROCESSLIST_ID
        AND session_connect_attrs.ATTR_NAME = "program_name"
    );
