DROP TABLE IF EXISTS custard;

CREATE TABLE custard
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

DROP TABLE IF EXISTS custard_a;
DROP TABLE IF EXISTS custard_b;

CREATE TABLE custard_a AS SELECT * FROM custard LIMIT 0;
CREATE TABLE custard_b AS SELECT * FROM custard LIMIT 0;
