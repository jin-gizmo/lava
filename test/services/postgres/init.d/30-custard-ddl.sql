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
    CustardJedi      BOOLEAN,
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

ALTER TABLE lava.custard OWNER TO lava;
ALTER TABLE lava.custard_tmp OWNER TO lava;
ALTER TABLE lava.custard_a OWNER TO lava;
ALTER TABLE lava.custard_b OWNER TO lava;

COPY lava.custard FROM '/data/custard100.csv' CSV HEADER;
