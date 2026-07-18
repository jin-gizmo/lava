-- Create the custard table typed columns - may be DB specific.

-- No Boolean in Oracle and dates are too much trouble for testing.

CREATE TABLE <{ db.common.schema }>.custard
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
    LastCustard      VARCHAR(20),
    CustardQuota     INTEGER
);

-- Create the _a / _b tables for switch loading tests
DROP TABLE <{ db.common.schema }>.custard_a;
DROP TABLE <{ db.common.schema }>.custard_b;

CREATE TABLE <{ db.common.schema }>.custard_a AS (
    SELECT *
    FROM <{ db.common.schema }>.custard
    WHERE ROWNUM < 0
);

CREATE TABLE <{ db.common.schema }>.custard_b AS (
    SELECT *
    FROM <{ db.common.schema }>.custard
    WHERE ROWNUM < 0
);

