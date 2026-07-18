DROP TABLE IF EXISTS lava.custard CASCADE;

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
    -- MySQL doesn't have a bool type and CSV loads fail into the tinyint(1)
    -- alternative
    CustardJedi      VARCHAR(5),
    City             VARCHAR(50),
    PostCode         VARCHAR(20),
    Email            VARCHAR(100),
    Phone            VARCHAR(20),
    LastCustard      DATE,
    CustardQuota     INTEGER
);

-- Create the _a / _b tables for switch loading tests
DROP TABLE IF EXISTS lava.custard_a CASCADE;
DROP TABLE IF EXISTS lava.custard_b CASCADE;
DROP TABLE IF EXISTS lava.custard_tmp CASCADE;

CREATE TABLE lava.custard_a
(
    LIKE lava.custard
);
CREATE TABLE lava.custard_b
(
    LIKE lava.custard
);
CREATE TABLE lava.custard_tmp
(
    LIKE lava.custard
);

-- Create a version with all fields as varchar.
-- This is a legacy thing for lava testing in MySQL.
DROP TABLE IF EXISTS lava.vcustard;
CREATE TABLE lava.vcustard
(
    ID               VARCHAR(20),
    CustardClubNo    VARCHAR(20),
    GivenName        VARCHAR(20),
    FamilyName       VARCHAR(30),
    Sex              VARCHAR(1),
    CustardBidPrice  VARCHAR(20),
    CustardCode      VARCHAR(10),
    FavouriteCustard VARCHAR(10),
    CustardJedi      VARCHAR(10),
    City             VARCHAR(50),
    PostCode         VARCHAR(20),
    Email            VARCHAR(100),
    Phone            VARCHAR(20),
    LastCustard      VARCHAR(30),
    CustardQuota     VARCHAR(20)
);


LOAD
DATA INFILE '/var/lib/mysql-files/custard100.csv'
INTO TABLE lava.custard
FIELDS TERMINATED BY ','
IGNORE 1 ROWS;

LOAD
DATA INFILE '/var/lib/mysql-files/custard100.csv'
INTO TABLE lava.vcustard
FIELDS TERMINATED BY ','
IGNORE 1 ROWS;

GRANT ALL PRIVILEGES ON lava.* TO lava;
