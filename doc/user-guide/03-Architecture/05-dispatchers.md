
## Lava Dispatchers

A lava dispatcher is a Lava worker that runs
[lavasched](#job-type-lavasched) jobs. Each realm must have at
least one dispatcher if jobs are to run on a schedule. The
[lavasched](#job-type-lavasched) job causes the crontab on the
node to be rebuilt with the list of jobs and their associated schedules.

While there can be multiple dispatchers in a realm (e.g. for load sharing or for
multiple timezones), each job can only be assigned to a single dispatcher. This
means that a worker that also serves as a dispatcher must be a singleton. It
cannot be part of an auto scaling group which allows more than one node to run.
