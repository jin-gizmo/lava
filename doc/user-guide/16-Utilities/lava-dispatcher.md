
## Lava Dispatcher Utility { data-toc-label="lava-dispatcher" }

The lava dispatcher utility is typically run by **cron(8)** to dispatch jobs on
a schedule. It can also be run as a stand-alone utility to dispatch jobs on
demand.

??? "Usage"

    ```bare
    usage: lava-dispatcher [-h] [--profile PROFILE] [-v] [--check-dispatch]
                           [-d DELAY] [-q QUEUE] [-r REALM] [-w WORKER]
                           [-g name=VALUE] [-p name=VALUE] [-c] [-l LEVEL]
                           [--log-json] [--log LOG] [--tag TAG]
                           job-id [job-id ...]

    Lava job dispatcher.

    options:
      -h, --help            show this help message and exit
      --profile PROFILE     As for AWS CLI.
      -v, --version         show program's version number and exit
      --check-dispatch      If specified, check for the the existence of a
                            dispatch suppression file "/tmp/lava/__nodispatch__".
                            If the file is present, all dispatches are suppressed.
                            This is typically only used for scheduled dispatches
                            when a dispatcher node is in the process of shutting
                            down.

    dispatch control options:
      -d DELAY, --delay DELAY
                            Delay dispatch by the specified duration. Default is
                            0. Maximum is 15 minutes.
      -q QUEUE, --queue QUEUE
                            AWS SQS queue name. If not specified, the queue name
                            is derived from the realm and worker name.
      -r REALM, --realm REALM
                            Lava realm name. Defaults to the value of the LAVA
                            REALM environment variable. A value must be specified
                            by one of these mechnisms.
      -w WORKER, --worker WORKER
                            Lava worker name. The worker must be a member of the
                            specified realm. If specified, the worker name must
                            match the value in the job specification. If not
                            specified, the correct value will be looked up in the
                            jobs table.

    job options:
      -g name=VALUE, --global name=VALUE
                            Additional global attribute to include in the job
                            dispatch event. This option can be used multiple
                            times. If global names contain dots, they will be
                            converted into a hierachy using the dots as level
                            separators.
      -p name=VALUE, --param name=VALUE
                            Additional parameter to include in the job dispatch
                            event. This option can be used multiple times. If
                            parameter names contain dots, they will be converted
                            into a hierarchy using the dots as level separators.
      job-id                One or more job IDs for the specified realm.

    logging arguments:
      -c, --no-colour, --no-color
                            Don't use colour in information messages.
      -l LEVEL, --level LEVEL
                            Print messages of a given severity level or above. The
                            standard logging level names are available but debug,
                            info, warning and error are most useful. The Default
                            is info.
      --log-json            Log messages in JSON format. This is particularly
                            useful when log messages end up in CloudWatch logs as
                            it simplifies searching.
      --log LOG             Log to the specified target. This can be either a file
                            name or a syslog facility with an @ prefix (e.g.
                            @local0).
      --tag TAG             Tag log entries with the specified value. The default
                            is lava-dispatcher.

    ```

See also [The Lava Dispatch Process](#the-lava-dispatch-process).

!!! info
    To enable JSON format logging when performing scheduled dispatches, add
    `--log-json` to the `args` parameter in the [lavasched](#job-type-lavasched)
    jobs.
