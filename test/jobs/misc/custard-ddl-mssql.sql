-- Create the custard table typed columns - may be DB specific.

-- No Boolean in SQL Server

CREATE TABLE [<{ db.common.schema }>].custard
(
    ID               INTEGER,
    CustardClubNo    INTEGER,
    GivenName        VARCHAR(20),
    FamilyName       VARCHAR(30),
    Sex              VARCHAR(1),
    CustardBidPrice  FLOAT(2),
    CustardCode      VARCHAR(10),
    FavouriteCustard VARCHAR(10),
    CustardJedi      VARCHAR(10),
    City             VARCHAR(50),
    PostCode         VARCHAR(20),
    Email            VARCHAR(100),
    Phone            VARCHAR(20),
    LastCustard DATE,
    CustardQuota     INTEGER
);

-- Create the _a / _b tables for switch loading tests
DROP TABLE [<{ db.common.schema }>].custard_a;
DROP TABLE [<{ db.common.schema }>].custard_b;

SELECT *
INTO [<{ db.common.schema }>].custard_a
FROM [<{ db.common.schema }>].custard
WHERE 1=0;

SELECT *
INTO [<{ db.common.schema }>].custard_b
FROM [<{ db.common.schema }>].custard
WHERE 1=0;

CREATE TABLE [lava].custard
(
    ID               INTEGER,
    CustardClubNo    INTEGER,
    GivenName        VARCHAR(20),
    FamilyName       VARCHAR(30),
    Sex              VARCHAR(1),
    CustardBidPrice  FLOAT(2),
    CustardCode      VARCHAR(10),
    FavouriteCustard VARCHAR(10),
    CustardJedi      VARCHAR(10),
    City             VARCHAR(50),
    PostCode         VARCHAR(20),
    Email            VARCHAR(100),
    Phone            VARCHAR(20),
    LastCustard DATE,
    CustardQuota     INTEGER
);

SELECT *
INTO [lava].custard_a
FROM [lava].custard
WHERE 1=0;

SELECT *
INTO [lava].custard_b
FROM [lava].custard
WHERE 1=0;
