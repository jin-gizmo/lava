-- Multiple SQL statements in a single file.

SELECT count(*)
FROM <{db.common.schema}>.{{ vars.table }};

INSERT INTO <{ db.common.schema }>.{{ vars.table }}
VALUES ('{{job.run_id}}');

-- Comment

-- Comment again

SELECT count(*)
FROM <{db.common.schema}>.{{ vars.table }};
