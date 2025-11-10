
## Lava Stop Utility { data-toc-label="lava-stop" }

The **lava-stop** utility initiates a controlled shutdown of the lava worker
daemons.

??? Usage

    ```bare
    usage: lava-stop [-h] [-D] [--profile PROFILE] [--signal SIGNAL] [-v]
                     [-w DURATION] [--auto-scaling-group-name NAME]
                     [--instance-id ID] [--lifecycle-action-token UUID]
                     [--lifecycle-hook-name NAME] [--lifecycle-heartbeat DURATION]
                     [-c] [-l LEVEL] [--log LOG] [--tag TAG]

    Stop lava worker processes.

    options:
      -h, --help            show this help message and exit
      -D, --no-dispatch     Inhibit further scheduled dispatches by creating
                            /tmp/lava/__nodispatch__. This requires the lava-
                            dispatcher utility to check for this file by
                            specifying the --check-dispatch argument.
      --profile PROFILE     As for AWS CLI.
      --signal SIGNAL, --sig SIGNAL
                            Send the specified signal to the lava worker
                            processes. Can be specified as a signal name (e.g.
                            SIGHUP or HUP) or a signal number. The default is 0
                            which only tests if the process exists. SIGHUP is
                            interpreted as a controlled shutdown instruction
                            allowing running jobs to complete. SIGTERM is
                            interpreted as a controlled, but immediate,
                            termination that allows final cleanup tasks but takes
                            no account of running jobs. See --w, --wait.
      -v, --version         show program's version number and exit
      -w DURATION, --wait DURATION
                            Wait for up to the specified duration for the lava
                            workers to finish voluntarily before killing them.
                            This requires the signal to be set to SIGHUP / HUP as
                            this is interpreted by the lava worker daemons as a
                            controlled shutdown request. The duration must be in
                            the form nn[X] where nn is a number and X is one of s
                            (seconds), m (minutes) or h (hours). If X is not
                            specified, seconds are assumed.

    AWS auto scaling lifecycle options:
      These arguments are designed to complete an AWS auto scaling "EC2
      Instance-terminate Lifecycle Action". See the AWS CLI or AWS auto scaling
      documentation for meaning and usage. Note that the lifecycle action result
      is always set to CONTINUE which means the auto scaling group _will_
      terminate the instance.

      --auto-scaling-group-name NAME
                            Send a complete-lifecycle-action signal for the
                            specified AWS auto scaing group. If specified,
                            --lifecycle-hook-name is also required.
      --instance-id ID      The ID of the EC2 instance (optional). If specified,
                            --auto-scaling-group-name / --lifecycle-hook-name are
                            required.
      --lifecycle-action-token UUID
                            lifecycle action identifier (optional). If specified,
                            --auto-scaling-group-name / --lifecycle-hook-name are
                            required.
      --lifecycle-hook-name NAME
                            The name of the AWS auto scaling lifecycle hook. If
                            specified, --auto-scaling-group-name is also required.
      --lifecycle-heartbeat DURATION
                            Record a heartbeat for the lifecycle action at
                            specified intervals (optional). If specified, --auto-
                            scaling-group-name / --lifecycle-hook-name are
                            required. THe duration must be in the form nn[X] where
                            nn is a number and X is one of s (seconds), m
                            (minutes) or h (hours). If X is not specified, seconds
                            are assumed. The minimum permitted value is 60
                            seconds.

    logging arguments:
      -c, --no-colour, --no-color
                            Don't use colour in information messages.
      -l LEVEL, --level LEVEL
                            Print messages of a given severity level or above. The
                            standard logging level names are available but debug,
                            info, warning and error are most useful. The Default
                            is info.
      --log LOG             Log to the specified target. This can be either a file
                            name or a syslog facility with an @ prefix (e.g.
                            @local0).
      --tag TAG             Tag log entries with the specified value. The default
                            is lava-stop.
    ```

The process for stopping a lava worker is:

1.  Send it a `SIGHUP` signal. This tells the worker to complete any in-flight
    or queued jobs but not to accept any more jobs.
    
2.  Wait a while.

3.  Send it another `SIGHUP` signal. The second `SIGHUP` is a more aggressive
    shutdown command and will interrupt in-flight jobs but still allow the
    worker an opportunity to cleanup.

4.  Give it another 10-20 seconds.

4.  If the worker is still running, kill it with `SIGKILL`.

**Lava-stop** will do a process listing to find worker processes. It can be used
interactively and is also designed for use within an AWS auto scaling
lifecycle hook for terminating worker nodes. This is all built in to a standard
lava deployment using the provided
[CloudFormation templates](#building-the-cloudformation-templates).
