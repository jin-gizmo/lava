ALTER SESSION SET CONTAINER = FREEPDB1;

DROP TABLE IF EXISTS lava.custard CASCADE CONSTRAINTS PURGE;

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
    CustardJedi      BOOLEAN,
    City             VARCHAR(50),
    PostCode         VARCHAR(20),
    Email            VARCHAR(100),
    Phone            VARCHAR(20),
    LastCustard      DATE,
    CustardQuota     INTEGER
);

-- Create the _a / _b tables for switch loading tests
DROP TABLE IF EXISTS lava.custard_a CASCADE CONSTRAINTS PURGE;
DROP TABLE IF EXISTS lava.custard_b CASCADE CONSTRAINTS PURGE;
DROP TABLE IF EXISTS lava.custard_tmp CASCADE CONSTRAINTS PURGE;

CREATE TABLE lava.custard_a
AS
SELECT *
FROM lava.custard
WHERE 1 = 2;

CREATE TABLE lava.custard_b
AS
SELECT *
FROM lava.custard
WHERE 1 = 2;

CREATE TABLE lava.custard_tmp
AS
SELECT *
FROM lava.custard
WHERE 1 = 2;

-- LOAD TABLE lava.custard FROM '/data/custard100.csv' CSV HEADER;
