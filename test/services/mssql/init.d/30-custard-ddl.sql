USE [lava]
GO

EXECUTE AS USER = '${DB_LAVA_USER}';
GO

DROP TABLE IF EXISTS lava.custard;
GO

CREATE TABLE lava.custard
(
    ID               INTEGER,
    CustardClubNo    INTEGER,
    GivenName        VARCHAR(20),
    FamilyName       VARCHAR(30),
    Sex              VARCHAR(1),
    CustardBidPrice  FLOAT(2),
    CustardCode      VARCHAR(10),
    FavouriteCustard VARCHAR(10),
    -- CustardJedi      BOOLEAN,
    -- MsSQL doesn't have a bool type
    -- alternative
    CustardJedi      VARCHAR(5),
    City             VARCHAR(50),
    PostCode         VARCHAR(20),
    Email            VARCHAR(100),
    Phone            VARCHAR(20),
    LastCustard      DATE,
    CustardQuota     INTEGER
);
GO

-- Create the _a / _b tables for switch loading tests

DROP TABLE IF EXISTS lava.custard_a;
DROP TABLE IF EXISTS lava.custard_b;
DROP TABLE IF EXISTS lava.custard_tmp;

SELECT *
INTO [lava].custard_a
FROM [lava].custard
WHERE 1 = 0;

SELECT *
INTO [lava].custard_b
FROM [lava].custard
WHERE 1 = 0;
GO

SELECT *
INTO [lava].custard_tmp
FROM [lava].custard
WHERE 1 = 0;
GO

REVERT;
GO

-- Load some test data
BULK INSERT lava.custard FROM '/data/custard100.csv'
    WITH (
    FIELDTERMINATOR = ',',
    ROWTERMINATOR = '\n',
    FIRSTROW = 2
    );
GO
