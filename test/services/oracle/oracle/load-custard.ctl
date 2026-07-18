LOAD DATA
INFILE '/data/custard100.csv'
APPEND INTO TABLE lava.custard
FIELDS TERMINATED BY ',' OPTIONALLY ENCLOSED BY '"'
TRAILING NULLCOLS
(
    ID,
    CustardClubNo,
    GivenName,
    FamilyName,
    Sex,
    CustardBidPrice,
    CustardCode,
    FavouriteCustard,
    CustardJedi,
    City,
    PostCode,
    Email,
    Phone,
    LastCustard DATE "YYYY-MM-DD",
    CustardQuota
)
