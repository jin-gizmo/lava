-- Query for program name in MsSQL

SELECT RTRIM(hostname)     AS hostname,
       RTRIM(program_name) AS program_name,
       RTRIM(loginame)     AS login_name,
       RTRIM(cmd)          AS cmd
FROM sys.sysprocesses
WHERE loginame != 'rdsa';
