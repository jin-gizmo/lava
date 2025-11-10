
### lavasched

#### Failing lavasched jobs

This is the result of a bad crontab spec in a newly added job.

Prior to version 5.0.0 (Cotopaxi), it could be tricky to localise the bad job
specification. Since Cotopaxi, output from
[lavasched](#job-type-lavasched) jobs now includes a context
diff of the new crontab vs the old one to simplify tracking of changes and
problem diagnosis.

