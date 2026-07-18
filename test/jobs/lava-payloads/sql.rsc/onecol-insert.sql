-- Insert current time as ISO timestamp into single col table

INSERT INTO <{db.common.schema}>.onecol
VALUES ('{{start.isoformat()[:-7]}}');
