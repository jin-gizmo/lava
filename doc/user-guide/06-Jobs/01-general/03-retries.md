
## Job Retries

By default, lava will make one attempt to run a job once dispatched and the job
will then either succeed or fail.

As of v6.1.0 (Volcán Pinta), lava supports a job retry mechanism that can retry
a failed job one or more times. This process is controlled by the following
fields in the [job specification](#the-jobs-table):

*   `iteration_limit`: specifies maximum number of attempts that will be made to
    run the job successfully before giving up

*   `iteration_delay`: The delay between run attempts.

The job will be re-run until either it succeeds or the `iteration_limit` is
reached. Lava makes an additional
[globals.lava.iteration](#globals-owned-by-lava) global
available for use with run-time Jinja rendering of job and action fields.

A single worker thread remains committed to the job for the entirety of the
retry process so it is important to use the retry mechanism sensibly.

!!! info
    The entire duration of the retry process must fit within the queue
    visibility timeout of the worker SQS queue or else SQS itself will resubmit
    the dispatch message, with the same run ID, while the first job is still
    running. This is not ideal.

### Job Actions for Retries

Lava makes the [on_retry](#job-actions) job action available
for situations where a job fails but will be retried in another iteration.

For example, if a job has an `iteration_count` of 2, and both attempts fail, the
`on_retry` actions will be executed after the first iteration and the `on_fail`
actions will be executed after the second and final iteration.

### Lava Job Retries (Iterations) vs SQS Resubmissions { data-toc-label="Retries vs Resubmissions" }

The [job specification](#the-jobs-table) contains both
`iterations_*` related fields and a `max_tries` fields.

The `iterations_*` related fields control internal job retry within the lava
worker.

The `max_tries` field controls how many times SQS is permitted to resubmit the
same dispatch message due to SQS queue visibility timeouts before it is
discarded by the lava worker.
