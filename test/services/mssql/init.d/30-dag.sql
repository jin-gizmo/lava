USE [lava]
GO

EXECUTE AS USER = '${DB_LAVA_USER}';
GO

DROP TABLE IF EXISTS lava.dag;
CREATE TABLE lava.dag
(
    job_group  VARCHAR(50),
    job        VARCHAR(50) NOT NULL,
    depends_on VARCHAR(50)
);

INSERT INTO lava.dag(job_group, job, depends_on)
VALUES ('1', 'J1', 'J3'),
       ('1', '', 'ignore'),
       ('1', 'J1', 'J5'),
       ('1', 'J2', NULL),
       ('1', 'J4', 'J1'),
       ('1', 'J4', 'J3'),
       ('2', 'J1', 'J3'),
       ('2', 'J1', 'J5'),
       ('2', 'J2', NULL),
       ('2', 'J3', 'J1'),
       ('2', 'J4', 'J1'),
       ('2', 'J4', 'J3');
GO

REVERT;
GO
