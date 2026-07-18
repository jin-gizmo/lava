SELECT {% if vars.limit %}TOP {{ vars.limit }}{% endif %} *
FROM <{db.common.schema}>.custard;
