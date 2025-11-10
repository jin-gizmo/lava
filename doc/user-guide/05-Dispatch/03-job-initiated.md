
## Job Initiated Dispatch

Lava has two mechanisms by which a job can dispatch other jobs.

### The Dispatch Job Type

The [dispatch](#job-type-dispatch) job type initiates the
dispatch of other jobs. This could be used, for example, as a step in a job
[chain](#job-type-chain).

### The Dispatch Job Action

Job [actions](#job-actions) are conditionally executed when a
job succeeds or fails. One of the available action types is the [dispatch
action](#action-type-dispatch).
