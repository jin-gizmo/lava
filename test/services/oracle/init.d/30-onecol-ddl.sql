-- Create a simple single column table.

ALTER SESSION SET CONTAINER = FREEPDB1;

DROP TABLE IF EXISTS lava.onecol;

CREATE TABLE lava.onecol
(
    x VARCHAR(50)
);
