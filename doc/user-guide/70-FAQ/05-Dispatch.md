
## Scheduling and Dispatch FAQ

### Scheduling

#### Can a job be scheduled to run when a worker reboots?

Yes … and no.

The `@reboot` crontab specification can be used in a job schedule
but what does that actually mean? Given that it will occur on the
dispatcher node, any job scheduled on a reboot will only get dispatched
when the dispatcher itself reboots. This may be useful, but it's not
obvious how.
