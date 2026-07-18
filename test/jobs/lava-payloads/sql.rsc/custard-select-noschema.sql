
SELECT * FROM custard {% if vars.limit %}LIMIT {{ vars.limit }}{% endif %};
