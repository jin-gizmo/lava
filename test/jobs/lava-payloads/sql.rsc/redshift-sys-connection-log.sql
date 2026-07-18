-- Serverless uses sys_connection_log not stl_connection_log
SELECT rtrim(user_name)         as user,
       substring(event, 1, 20) as event,
       record_time,
       rtrim(remote_host)       as host,
       rtrim(auth_method)       as auth,
       rtrim(ssl_version)       as ssl,
       rtrim(application_name) as app_name
FROM sys_connection_log
WHERE user_name like '%lava%'
ORDER BY record_time desc
LIMIT 5;
