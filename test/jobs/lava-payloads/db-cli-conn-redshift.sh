#!/bin/bash

[ "$LAVA_CONN_DB" = "" ] && echo $0: LAVA_CONN_DB not set && exit 1

$LAVA_CONN_DB <<!
SELECT rtrim(username) as user,
       substring(event,1,20) as event,
       recordtime,
       rtrim(remotehost) as host,
       rtrim(authmethod) as auth,
       rtrim(sslversion) as ssl,
       rtrim(application_name) as app_name
FROM stl_connection_log
WHERE username like '%lava%'
ORDER BY recordtime desc
LIMIT 5;
!
