
SELECT * FROM <{db.common.schema}>.custard {% if vars.limit %}LIMIT {{ vars.limit }}{% endif %};
