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
