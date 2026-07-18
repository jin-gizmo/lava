-- Initialise a database

IF NOT EXISTS(SELECT *
              FROM sys.databases
              WHERE name = 'lava')
    BEGIN
        CREATE DATABASE [lava]
        PRINT 'Database lava created'
    END
ELSE
    BEGIN
        PRINT 'Database lava exists - skipping'
    END
GO
