-- Create the partitions table for Redshift indirect partitions.

DROP TABLE IF EXISTS "<{ db.common.schema }>".partitions;

CREATE TABLE "<{ db.common.schema }>".partitions
(
    schema_name VARCHAR(127)  NOT NULL,
    rel_name    VARCHAR(127)  NOT NULL,
    partitions  VARCHAR(2048) NOT NULL,
    PRIMARY KEY (schema_name, rel_name)
);

-- Create entries for testing
INSERT INTO "<{ db.common.schema }>".partitions
VALUES ('<{ db.common.schema }>', 'custard', 'sex,favouritecustard');

