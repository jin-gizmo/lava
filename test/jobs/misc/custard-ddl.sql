-- Create the custard table typed columns - may be DB specific.

DROP TABLE IF EXISTS <{ db.common.schema }>.custard;

CREATE TABLE <{ db.common.schema }>.custard (
  ID INTEGER,
  CustardClubNo INTEGER,
  GivenName VARCHAR(20),
  FamilyName VARCHAR(30),
  Sex VARCHAR(1),
  CustardBidPrice FLOAT(2),
  CustardCode VARCHAR(10),
  FavouriteCustard VARCHAR(10),
  CustardJedi BOOLEAN,
  City VARCHAR(50),
  PostCode VARCHAR(20),
  Email VARCHAR(100),
  Phone VARCHAR(20),
  LastCustard DATE,
  CustardQuota INTEGER
);

-- Create the _a / _b tables for switch loading tests
DROP TABLE IF EXISTS <{ db.common.schema }>.custard_a;
DROP TABLE IF EXISTS <{ db.common.schema }>.custard_b;

CREATE TABLE <{ db.common.schema }>.custard_a (LIKE <{ db.common.schema }>.custard);
CREATE TABLE <{ db.common.schema }>.custard_b (LIKE <{ db.common.schema }>.custard);
