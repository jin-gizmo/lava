-- Create the lava user
USE [lava]
GO

IF EXISTS (SELECT 1
           FROM sys.database_principals
           WHERE name = '${DB_LAVA_USER}'
             AND type = 'S')
    BEGIN
        PRINT 'User ${DB_LAVA_USER} exists - skipping';
    END
ELSE
    BEGIN
        CREATE LOGIN ${DB_LAVA_USER} WITH PASSWORD = '${DB_LAVA_PASSWORD}';
        CREATE USER ${DB_LAVA_USER} FOR LOGIN ${DB_LAVA_USER};
    END
GO

GRANT CREATE TABLE TO ${DB_LAVA_USER};
