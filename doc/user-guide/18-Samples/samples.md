*   [Job samples](#job-samples)
*   [Connection samples](#connection-samples)
*   [Rule samples](#rule-samples)
*   [S3trigger samples](#s3trigger-samples)

## Job Samples
??? "chain"

    ```yaml
    
    ## #############################################################################
    ## Mandatory fields
    
    enabled: true
    job_id: "<{ prefix.job }>/demo"
    worker: "<{ worker.main }>"
    
    description: "What does this job do?"
    owner: "<{ owner }>"
    
    ## #############################################################################
    ## Optional fields
    ##
    
    ## - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
    ## Dispatcher name
    ##
    ## For scheduled jobs it will be something like...
    # dispatcher: "<{ dispatcher.main }>"
    ##
    ## For non-scheduled jobs it will be omitted
    
    ## - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
    ## enable/disable generation of CloudWatch custom metrics for this job.
    ## If not set, use realm level setting.
    ##
    # cw_metrics: true
    
    ## - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
    ## Log specified information in the events table before the first iteration
    ## commences. Can be a string or an arbitrary object. DON'T LOG SECRETS.
    ##
    # event_log: ...
    
    ## - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
    ## Limit the number of times a single SQS dispatch message can be processed.
    ## Default is 0 which means the limit is determined by SQS queue and worker config.
    ##
    # max_tries: 0
    
    ## - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
    ## Lava internal retry control
    ##
    # iteration_limit: 1
    # iteration_delay: 0s
    
    ## - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
    ## Simplest form is cron(1) style schedule.
    ##
    # schedule: "<{ schedule.main }>"
    
    ## - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
    ## Global values.
    ##
    # globals:
    #   global1: "value1"
    #   global2: "value2"
    
    ## - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
    ## Post job actions. If not specified here, the realm level values are used.
    ## Can have list of multiple actions.
    ##
    # on_success:
    #   - action: action-type
    #     param1: ...
    #     param2: ...
    #
    # on_retry:
    #   - action: action-type
    #     param1: ...
    #     param2: ...
    #
    # on_fail:
    #   - action: action-type
    #     param1: ...
    #     param2: ...
    
    ## - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
    ## X-* / x-* vars are ignored by lava but may be useful for other purposes.
    ##
    # X-whatever: "Some value"
    
    type: chain
    
    ## #############################################################################
    ## The payload is either a comma separated list of job_ids or an actual list of
    ## job_ids.
    ##
    payload:
      - "job1"
      - "job2"
      - "..."
    
    ## #############################################################################
    ## Job parameters
    
    parameters:
      ## ---------------------------------------------------------------------------
      ## Mandatory params
    
      ## ---------------------------------------------------------------------------
      ## Optional params
    
      ## - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
      ## Prepend the specified value to each job_id in the payload.
      # job_prefix: "app/myjobs/"
    
      ## - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
      ## The job_id of the starting point in the chain. Defaults to first in list.
      # start: "start_job_id"
    
      ## - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
      ## Child jobs matching this glob pattern (or any in a list of patterns) are
      ## allowed to fail without causing the chain to fail.
      # can_fail: "glob-pattern"
    ```

??? "cmd"

    ```yaml
    
    ## #############################################################################
    ## Mandatory fields
    
    enabled: true
    job_id: "<{ prefix.job }>/demo"
    worker: "<{ worker.main }>"
    
    description: "What does this job do?"
    owner: "<{ owner }>"
    
    ## #############################################################################
    ## Optional fields
    ##
    
    ## - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
    ## Dispatcher name
    ##
    ## For scheduled jobs it will be something like...
    # dispatcher: "<{ dispatcher.main }>"
    ##
    ## For non-scheduled jobs it will be omitted
    
    ## - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
    ## enable/disable generation of CloudWatch custom metrics for this job.
    ## If not set, use realm level setting.
    ##
    # cw_metrics: true
    
    ## - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
    ## Log specified information in the events table before the first iteration
    ## commences. Can be a string or an arbitrary object. DON'T LOG SECRETS.
    ##
    # event_log: ...
    
    ## - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
    ## Limit the number of times a single SQS dispatch message can be processed.
    ## Default is 0 which means the limit is determined by SQS queue and worker config.
    ##
    # max_tries: 0
    
    ## - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
    ## Lava internal retry control
    ##
    # iteration_limit: 1
    # iteration_delay: 0s
    
    ## - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
    ## Simplest form is cron(1) style schedule.
    ##
    # schedule: "<{ schedule.main }>"
    
    ## - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
    ## Global values.
    ##
    # globals:
    #   global1: "value1"
    #   global2: "value2"
    
    ## - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
    ## Post job actions. If not specified here, the realm level values are used.
    ## Can have list of multiple actions.
    ##
    # on_success:
    #   - action: action-type
    #     param1: ...
    #     param2: ...
    #
    # on_retry:
    #   - action: action-type
    #     param1: ...
    #     param2: ...
    #
    # on_fail:
    #   - action: action-type
    #     param1: ...
    #     param2: ...
    
    ## - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
    ## X-* / x-* vars are ignored by lava but may be useful for other purposes.
    ##
    # X-whatever: "Some value"
    
    type: cmd
    
    ## #############################################################################
    ## The payload is the command string. This will be parsed using standard Linux
    ## shell lexical analysis to determine the executable and arguments. Additional
    ## arguments can also be specified with the args parameter
    ##
    payload: "???"
    
    ## #############################################################################
    ## Job parameters
    
    parameters:
      ## ---------------------------------------------------------------------------
      ## Mandatory params
    
      ## ---------------------------------------------------------------------------
      ## Optional params
    
      ## - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
      ## A list of additional arguments for the executable(s) specified in payload.
      ##
      # args:
      #   - "arg1"
      #   - "arg2"
    
      ## - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
      ## A map of additional environment variables for the exe.
      ##
      # env:
      #   env_var1: "value1"
      #   env_var2: "value2"
    
      ## - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
      ## Enable / disable jinja rendering. Default is true. If false, disable Jinja
      ## rendering of the args. Default true.
      ##
      # jinja: true
    
      ## - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
      ## Job timeout. Default is 10 minutes. Values are in the form nnX where nn is
      ## a number and X is s (seconds), m (minutes) or h (hours). If payload is a
      ## list, this is applied to each individual exe.
      ##
      # timeout: "10m"
    
      ## - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
      ## A map of variables injected when the command arguments and environment are
      ## Jinja rendered.
      ##
      # vars:
      #   var1: value1
      #   var2: value2
    ```

??? "dag"

    ```yaml
    
    ## #############################################################################
    ## Mandatory fields
    
    enabled: true
    job_id: "<{ prefix.job }>/demo"
    worker: "<{ worker.main }>"
    
    description: "What does this job do?"
    owner: "<{ owner }>"
    
    ## #############################################################################
    ## Optional fields
    ##
    
    ## - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
    ## Dispatcher name
    ##
    ## For scheduled jobs it will be something like...
    # dispatcher: "<{ dispatcher.main }>"
    ##
    ## For non-scheduled jobs it will be omitted
    
    ## - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
    ## enable/disable generation of CloudWatch custom metrics for this job.
    ## If not set, use realm level setting.
    ##
    # cw_metrics: true
    
    ## - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
    ## Log specified information in the events table before the first iteration
    ## commences. Can be a string or an arbitrary object. DON'T LOG SECRETS.
    ##
    # event_log: ...
    
    ## - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
    ## Limit the number of times a single SQS dispatch message can be processed.
    ## Default is 0 which means the limit is determined by SQS queue and worker config.
    ##
    # max_tries: 0
    
    ## - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
    ## Lava internal retry control
    ##
    # iteration_limit: 1
    # iteration_delay: 0s
    
    ## - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
    ## Simplest form is cron(1) style schedule.
    ##
    # schedule: "<{ schedule.main }>"
    
    ## - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
    ## Global values.
    ##
    # globals:
    #   global1: "value1"
    #   global2: "value2"
    
    ## - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
    ## Post job actions. If not specified here, the realm level values are used.
    ## Can have list of multiple actions.
    ##
    # on_success:
    #   - action: action-type
    #     param1: ...
    #     param2: ...
    #
    # on_retry:
    #   - action: action-type
    #     param1: ...
    #     param2: ...
    #
    # on_fail:
    #   - action: action-type
    #     param1: ...
    #     param2: ...
    
    ## - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
    ## X-* / x-* vars are ignored by lava but may be useful for other purposes.
    ##
    # X-whatever: "Some value"
    
    type: dag
    
    ## #############################################################################
    ## The payload is either a map of job dependencies. Keys are successor jobs and
    ## values are lists of predecessor jobs or null / [] when no predecessors.
    ## job_ids.
    ##
    payload:
      "job1":
        - "predecessor_1"
        - "predecessor_2"
      "job2": "just_one_predecessor"
      "job3": null
    
    ## #############################################################################
    ## Job parameters
    
    parameters:
      ## ---------------------------------------------------------------------------
      ## Mandatory params
    
      ## ---------------------------------------------------------------------------
      ## Optional params
    
      ## - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
      ## Prepend the specified value to each job_id in the payload.
      # job_prefix: "app/myjobs/"
    
      ## - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
      ## Thread pool size for running child jobs. Don't get carried away.
      # workers: 4
    
      ## - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
      ## Child jobs matching this glob pattern (or any in a list of patterns) are
      ## allowed to fail without causing the chain to fail.
      # can_fail: "glob-pattern"
    ```

??? "db_from_s3"

    ```yaml
    
    ## #############################################################################
    ## Mandatory fields
    
    enabled: true
    job_id: "<{ prefix.job }>/demo"
    worker: "<{ worker.main }>"
    
    description: "What does this job do?"
    owner: "<{ owner }>"
    
    ## #############################################################################
    ## Optional fields
    ##
    
    ## - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
    ## Dispatcher name
    ##
    ## For scheduled jobs it will be something like...
    # dispatcher: "<{ dispatcher.main }>"
    ##
    ## For non-scheduled jobs it will be omitted
    
    ## - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
    ## enable/disable generation of CloudWatch custom metrics for this job.
    ## If not set, use realm level setting.
    ##
    # cw_metrics: true
    
    ## - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
    ## Log specified information in the events table before the first iteration
    ## commences. Can be a string or an arbitrary object. DON'T LOG SECRETS.
    ##
    # event_log: ...
    
    ## - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
    ## Limit the number of times a single SQS dispatch message can be processed.
    ## Default is 0 which means the limit is determined by SQS queue and worker config.
    ##
    # max_tries: 0
    
    ## - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
    ## Lava internal retry control
    ##
    # iteration_limit: 1
    # iteration_delay: 0s
    
    ## - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
    ## Simplest form is cron(1) style schedule.
    ##
    # schedule: "<{ schedule.main }>"
    
    ## - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
    ## Global values.
    ##
    # globals:
    #   global1: "value1"
    #   global2: "value2"
    
    ## - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
    ## Post job actions. If not specified here, the realm level values are used.
    ## Can have list of multiple actions.
    ##
    # on_success:
    #   - action: action-type
    #     param1: ...
    #     param2: ...
    #
    # on_retry:
    #   - action: action-type
    #     param1: ...
    #     param2: ...
    #
    # on_fail:
    #   - action: action-type
    #     param1: ...
    #     param2: ...
    
    ## - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
    ## X-* / x-* vars are ignored by lava but may be useful for other purposes.
    ##
    # X-whatever: "Some value"
    
    type: db_from_s3
    
    ## #############################################################################
    ## The payload is ignored.
    ##
    payload: "--"
    
    ## #############################################################################
    ## Job parameters
    
    parameters:
      ## ---------------------------------------------------------------------------
      ## Mandatory params
    
      db_conn_id: "???"
      bucket: "???"
      key: "???"
      schema: "???"
      table: "???"
      mode: "???"
    
      ## ---------------------------------------------------------------------------
      ## Optional params
    
      ## Skip missing files without throwing an error.
      # skip_missing: false
    
      ## - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
      ## S3 connectivity -- either s3_conn_id or s3_iam_role
      ##
      ## The connection ID for AWS S3.
      # s3_conn_id: "???"
      ## The IAM role name used to allow access to the source data in S3.
      # s3_iam_role: "???"
    
    
      ## - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
      ## A list of additional arguments dependent on target DB type
      # args:
      #   - "arg1"
      #   - "arg2"
    
      ## - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
      ## List of SQL column specifications.
      # columns:
      #  - "col1 VARCHAR(20)"
      #  - "col2 TIMESTAMP"
    ```

??? "dispatch"

    ```yaml
    
    ## #############################################################################
    ## Mandatory fields
    
    enabled: true
    job_id: "<{ prefix.job }>/demo"
    worker: "<{ worker.main }>"
    
    description: "What does this job do?"
    owner: "<{ owner }>"
    
    ## #############################################################################
    ## Optional fields
    ##
    
    ## - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
    ## Dispatcher name
    ##
    ## For scheduled jobs it will be something like...
    # dispatcher: "<{ dispatcher.main }>"
    ##
    ## For non-scheduled jobs it will be omitted
    
    ## - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
    ## enable/disable generation of CloudWatch custom metrics for this job.
    ## If not set, use realm level setting.
    ##
    # cw_metrics: true
    
    ## - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
    ## Log specified information in the events table before the first iteration
    ## commences. Can be a string or an arbitrary object. DON'T LOG SECRETS.
    ##
    # event_log: ...
    
    ## - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
    ## Limit the number of times a single SQS dispatch message can be processed.
    ## Default is 0 which means the limit is determined by SQS queue and worker config.
    ##
    # max_tries: 0
    
    ## - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
    ## Lava internal retry control
    ##
    # iteration_limit: 1
    # iteration_delay: 0s
    
    ## - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
    ## Simplest form is cron(1) style schedule.
    ##
    # schedule: "<{ schedule.main }>"
    
    ## - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
    ## Global values.
    ##
    # globals:
    #   global1: "value1"
    #   global2: "value2"
    
    ## - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
    ## Post job actions. If not specified here, the realm level values are used.
    ## Can have list of multiple actions.
    ##
    # on_success:
    #   - action: action-type
    #     param1: ...
    #     param2: ...
    #
    # on_retry:
    #   - action: action-type
    #     param1: ...
    #     param2: ...
    #
    # on_fail:
    #   - action: action-type
    #     param1: ...
    #     param2: ...
    
    ## - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
    ## X-* / x-* vars are ignored by lava but may be useful for other purposes.
    ##
    # X-whatever: "Some value"
    
    type: dispatch
    
    ## #############################################################################
    ## The payload is either a comma separated list of job_ids or an actual list of
    ## job_ids.
    ##
    payload:
      - "job1"
      - "job2"
      - "..."
    
    ## #############################################################################
    ## Job parameters
    
    parameters:
      ## ---------------------------------------------------------------------------
      ## Mandatory params
    
      ## ---------------------------------------------------------------------------
      ## Optional params
    
      ## - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
      ## Dispatch message sending delay in the form nnX where nn is a number and X
      ## is s (seconds) or m (minutes). The maximum allowed value is 15 minutes.
      ##
      # delay: "5m"
    
      ## - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
      ## If false, disable Jinja rendering of the payload. Default true.
      ##
      # jinja: true
    
      ## - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
      ## Prepend the specified value to each job_id in the payload.
      # job_prefix: "app/myjobs/"
    
      ## - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
      ## A map of parameters that will be passed to the jobs being dispatched. This
      ## is Jinja rendered.
      ##
      # parameters:
      #   p1: "v1"
      #   p2: "v2"
    ```

??? "docker"

    ```yaml
    
    ## #############################################################################
    ## Mandatory fields
    
    enabled: true
    job_id: "<{ prefix.job }>/demo"
    worker: "<{ worker.main }>"
    
    description: "What does this job do?"
    owner: "<{ owner }>"
    
    ## #############################################################################
    ## Optional fields
    ##
    
    ## - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
    ## Dispatcher name
    ##
    ## For scheduled jobs it will be something like...
    # dispatcher: "<{ dispatcher.main }>"
    ##
    ## For non-scheduled jobs it will be omitted
    
    ## - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
    ## enable/disable generation of CloudWatch custom metrics for this job.
    ## If not set, use realm level setting.
    ##
    # cw_metrics: true
    
    ## - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
    ## Log specified information in the events table before the first iteration
    ## commences. Can be a string or an arbitrary object. DON'T LOG SECRETS.
    ##
    # event_log: ...
    
    ## - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
    ## Limit the number of times a single SQS dispatch message can be processed.
    ## Default is 0 which means the limit is determined by SQS queue and worker config.
    ##
    # max_tries: 0
    
    ## - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
    ## Lava internal retry control
    ##
    # iteration_limit: 1
    # iteration_delay: 0s
    
    ## - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
    ## Simplest form is cron(1) style schedule.
    ##
    # schedule: "<{ schedule.main }>"
    
    ## - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
    ## Global values.
    ##
    # globals:
    #   global1: "value1"
    #   global2: "value2"
    
    ## - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
    ## Post job actions. If not specified here, the realm level values are used.
    ## Can have list of multiple actions.
    ##
    # on_success:
    #   - action: action-type
    #     param1: ...
    #     param2: ...
    #
    # on_retry:
    #   - action: action-type
    #     param1: ...
    #     param2: ...
    #
    # on_fail:
    #   - action: action-type
    #     param1: ...
    #     param2: ...
    
    ## - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
    ## X-* / x-* vars are ignored by lava but may be useful for other purposes.
    ##
    # X-whatever: "Some value"
    
    type: docker
    
    ## #############################################################################
    ## The payload is the container repository and, optionally, tag in the form
    ## repository[:tag]. If the tag is not specified, a tag of latest is used.
    ##
    payload: "<{ lava.aws.ecr_uri }>/<{ prefix.docker_repo }>/???"
    
    ## #############################################################################
    ## Job parameters
    
    parameters:
      ## ---------------------------------------------------------------------------
      ## Mandatory params
    
      ## ---------------------------------------------------------------------------
      ## Optional params
    
      ## - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
      ## The command to run in the container. If not specified, the default entry
      ## point for the container is used.
      # command: "???"
    
      ## - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
      ## The conn_id for connecting to docker. If not specified, a value must be
      ## specified for the entire realm in the realms table.
      # docker: conn_id_for_docker_registry
    
      ## - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
      ## A list of additional arguments for the executable(s) specified in payload.
      # args:
      #   - "arg1"
      #   - "arg2"
    
      ## - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
      ## Keys are connection labels and the values are conn_id.
      # connections:
      #     conn1: "conn1_id"
      #     conn2: "conn2_id"
    
      ## - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
      ## A map of additional environment variables for the exe.
      ##
      # env:
      #   env_var1: "value1"
      #   env_var2: "value2"
    
      ## - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
      ## Enable / disable jinja rendering. Default is true. If false, disable Jinja
      ## rendering of the args. Default true.
      ##
      # jinja: true
    
      ## - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
      ## Job timeout. Default is 10 minutes. Values are in the form nnX where nn is
      ## a number and X is s (seconds), m (minutes) or h (hours). If payload is a
      ## list, this is applied to each individual exe.
      ##
      # timeout: "10m"
    
      ## - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
      ## A map of variables injected when the command arguments and environment are
      ## Jinja rendered.
      ##
      # vars:
      #   var1: "value1"
      #   var2: "value2"
    
      ## - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
      # A map of container host configuration parameters.
      # host_config:
      #   blkio_weight: ??
      #   blkio_weight_device: ??
      #   cap_add: ??
      #   cap_drop: ??
      #   cpu_count: ??
      #   cpu_percent: ??
      #   cpu_period: ??
      #   cpu_quota: ??
      #   cpu_shares: ??
      #   cpuset_cpus: ??
      #   cpuset_mems: ??
      #   device_read_bps: ??
      #   device_read_iops: ??
      #   device_write_bps: ??
      #   device_write_iops: ??
      #   dns: ??
      #   dns_opt: ??
      #   dns_search: ??
      #   domainname: ??
      #   extra_hosts: ??
      #   group_add: ??
      #   mem_limit: ??
      #   mem_swappiness: ??
      #   memswap_limit: ??
      #   nano_cpus: ??
      #   network_disabled: ??
      #   network_mode: ??
      #   ports: ??
      #   publish_all_ports: ??
      #   shm_size: ??
      #   user: ??
      #   working_dir: ??
    ```

??? "exe"

    ```yaml
    
    ## #############################################################################
    ## Mandatory fields
    
    enabled: true
    job_id: "<{ prefix.job }>/demo"
    worker: "<{ worker.main }>"
    
    description: "What does this job do?"
    owner: "<{ owner }>"
    
    ## #############################################################################
    ## Optional fields
    ##
    
    ## - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
    ## Dispatcher name
    ##
    ## For scheduled jobs it will be something like...
    # dispatcher: "<{ dispatcher.main }>"
    ##
    ## For non-scheduled jobs it will be omitted
    
    ## - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
    ## enable/disable generation of CloudWatch custom metrics for this job.
    ## If not set, use realm level setting.
    ##
    # cw_metrics: true
    
    ## - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
    ## Log specified information in the events table before the first iteration
    ## commences. Can be a string or an arbitrary object. DON'T LOG SECRETS.
    ##
    # event_log: ...
    
    ## - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
    ## Limit the number of times a single SQS dispatch message can be processed.
    ## Default is 0 which means the limit is determined by SQS queue and worker config.
    ##
    # max_tries: 0
    
    ## - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
    ## Lava internal retry control
    ##
    # iteration_limit: 1
    # iteration_delay: 0s
    
    ## - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
    ## Simplest form is cron(1) style schedule.
    ##
    # schedule: "<{ schedule.main }>"
    
    ## - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
    ## Global values.
    ##
    # globals:
    #   global1: "value1"
    #   global2: "value2"
    
    ## - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
    ## Post job actions. If not specified here, the realm level values are used.
    ## Can have list of multiple actions.
    ##
    # on_success:
    #   - action: action-type
    #     param1: ...
    #     param2: ...
    #
    # on_retry:
    #   - action: action-type
    #     param1: ...
    #     param2: ...
    #
    # on_fail:
    #   - action: action-type
    #     param1: ...
    #     param2: ...
    
    ## - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
    ## X-* / x-* vars are ignored by lava but may be useful for other purposes.
    ##
    # X-whatever: "Some value"
    
    type: exe
    
    ## #############################################################################
    ## Payload is the path to an executable (or list of paths) relative to the
    ## payloads area in S3.
    ##
    payload: "<{ prefix.payload }>/???"
    
    ## #############################################################################
    ## Job parameters
    
    parameters:
      ## ---------------------------------------------------------------------------
      ## Mandatory params
    
      ## ---------------------------------------------------------------------------
      ## Optional params
    
      ## - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
      ## A list of additional arguments for the executable(s) specified in payload.
      ##
      # args:
      #   - "arg1"
      #   - "arg2"
    
      ## - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
      ## Keys are connection labels and the values are conn_id.
      ##
      # connections:
      #     conn1: "conn1_id"
      #     conn2: "conn2_id"
    
      ## - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
      ## A map of additional environment variables for the exe.
      ##
      # env:
      #   env_var1: "value1"
      #   env_var2: "value2"
    
      ## - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
      ## Enable / disable jinja rendering. Default is true. If false, disable Jinja
      ## rendering of the args. Default true.
      ##
      # jinja: true
    
      ## - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
      ## Job timeout. Default is 10 minutes. Values are in the form nnX where nn is
      ## a number and X is s (seconds), m (minutes) or h (hours). If payload is a
      ## list, this is applied to each individual exe.
      ##
      # timeout: "10m"
    
      ## - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
      ## A map of variables injected when the command arguments and environment are
      ## Jinja rendered.
      ##
      # vars:
      #   var1: "value1"
      #   var2: "value2"
    ```

??? "foreach"

    ```yaml
    
    ## #############################################################################
    ## Mandatory fields
    
    enabled: true
    job_id: "<{ prefix.job }>/demo"
    worker: "<{ worker.main }>"
    
    description: "What does this job do?"
    owner: "<{ owner }>"
    
    ## #############################################################################
    ## Optional fields
    ##
    
    ## - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
    ## Dispatcher name
    ##
    ## For scheduled jobs it will be something like...
    # dispatcher: "<{ dispatcher.main }>"
    ##
    ## For non-scheduled jobs it will be omitted
    
    ## - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
    ## enable/disable generation of CloudWatch custom metrics for this job.
    ## If not set, use realm level setting.
    ##
    # cw_metrics: true
    
    ## - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
    ## Log specified information in the events table before the first iteration
    ## commences. Can be a string or an arbitrary object. DON'T LOG SECRETS.
    ##
    # event_log: ...
    
    ## - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
    ## Limit the number of times a single SQS dispatch message can be processed.
    ## Default is 0 which means the limit is determined by SQS queue and worker config.
    ##
    # max_tries: 0
    
    ## - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
    ## Lava internal retry control
    ##
    # iteration_limit: 1
    # iteration_delay: 0s
    
    ## - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
    ## Simplest form is cron(1) style schedule.
    ##
    # schedule: "<{ schedule.main }>"
    
    ## - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
    ## Global values.
    ##
    # globals:
    #   global1: "value1"
    #   global2: "value2"
    
    ## - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
    ## Post job actions. If not specified here, the realm level values are used.
    ## Can have list of multiple actions.
    ##
    # on_success:
    #   - action: action-type
    #     param1: ...
    #     param2: ...
    #
    # on_retry:
    #   - action: action-type
    #     param1: ...
    #     param2: ...
    #
    # on_fail:
    #   - action: action-type
    #     param1: ...
    #     param2: ...
    
    ## - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
    ## X-* / x-* vars are ignored by lava but may be useful for other purposes.
    ##
    # X-whatever: "Some value"
    
    type: foreach
    
    ## #############################################################################
    ## The payload is the job_id for the child job to be run iteratively.
    ##
    payload: "child_job_id"
    
    ## #############################################################################
    ## Job parameters
    
    parameters:
      ## ---------------------------------------------------------------------------
      ## Mandatory params
    
      foreach:
        type: "iterator type"  # e.g. inline, csv etc.
        param1: ...  # These are type dependent
        param2: ...
    
      ## ---------------------------------------------------------------------------
      ## Optional params
    
      ## - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
      ## Child job iterations are allowed to fail without causing the main job to fail.
      # can_fail: false
    
      ## - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
      ## Enable / disable jinja rendering. Default is true. If false, disable Jinja
      ## rendering of the args. Default true.
      ##
      # jinja: true
    
      ## - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
      ## Abort without running any jobs if the loop is longer than this.
      # limit: 5
    ```

??? "log"

    ```yaml
    
    ## #############################################################################
    ## Mandatory fields
    
    enabled: true
    job_id: "<{ prefix.job }>/demo"
    worker: "<{ worker.main }>"
    
    description: "What does this job do?"
    owner: "<{ owner }>"
    
    ## #############################################################################
    ## Optional fields
    ##
    
    ## - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
    ## Dispatcher name
    ##
    ## For scheduled jobs it will be something like...
    # dispatcher: "<{ dispatcher.main }>"
    ##
    ## For non-scheduled jobs it will be omitted
    
    ## - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
    ## enable/disable generation of CloudWatch custom metrics for this job.
    ## If not set, use realm level setting.
    ##
    # cw_metrics: true
    
    ## - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
    ## Log specified information in the events table before the first iteration
    ## commences. Can be a string or an arbitrary object. DON'T LOG SECRETS.
    ##
    # event_log: ...
    
    ## - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
    ## Limit the number of times a single SQS dispatch message can be processed.
    ## Default is 0 which means the limit is determined by SQS queue and worker config.
    ##
    # max_tries: 0
    
    ## - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
    ## Lava internal retry control
    ##
    # iteration_limit: 1
    # iteration_delay: 0s
    
    ## - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
    ## Simplest form is cron(1) style schedule.
    ##
    # schedule: "<{ schedule.main }>"
    
    ## - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
    ## Global values.
    ##
    # globals:
    #   global1: "value1"
    #   global2: "value2"
    
    ## - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
    ## Post job actions. If not specified here, the realm level values are used.
    ## Can have list of multiple actions.
    ##
    # on_success:
    #   - action: action-type
    #     param1: ...
    #     param2: ...
    #
    # on_retry:
    #   - action: action-type
    #     param1: ...
    #     param2: ...
    #
    # on_fail:
    #   - action: action-type
    #     param1: ...
    #     param2: ...
    
    ## - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
    ## X-* / x-* vars are ignored by lava but may be useful for other purposes.
    ##
    # X-whatever: "Some value"
    
    type: log
    
    ## #############################################################################
    ## The payload is ignored.
    ##
    payload: "--"
    
    ## #############################################################################
    ## Job parameters
    
    parameters:
      ## ---------------------------------------------------------------------------
      ## Mandatory params
    
      ## ---------------------------------------------------------------------------
      ## Optional params
    ```

??? "pkg"

    ```yaml
    
    ## #############################################################################
    ## Mandatory fields
    
    enabled: true
    job_id: "<{ prefix.job }>/demo"
    worker: "<{ worker.main }>"
    
    description: "What does this job do?"
    owner: "<{ owner }>"
    
    ## #############################################################################
    ## Optional fields
    ##
    
    ## - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
    ## Dispatcher name
    ##
    ## For scheduled jobs it will be something like...
    # dispatcher: "<{ dispatcher.main }>"
    ##
    ## For non-scheduled jobs it will be omitted
    
    ## - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
    ## enable/disable generation of CloudWatch custom metrics for this job.
    ## If not set, use realm level setting.
    ##
    # cw_metrics: true
    
    ## - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
    ## Log specified information in the events table before the first iteration
    ## commences. Can be a string or an arbitrary object. DON'T LOG SECRETS.
    ##
    # event_log: ...
    
    ## - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
    ## Limit the number of times a single SQS dispatch message can be processed.
    ## Default is 0 which means the limit is determined by SQS queue and worker config.
    ##
    # max_tries: 0
    
    ## - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
    ## Lava internal retry control
    ##
    # iteration_limit: 1
    # iteration_delay: 0s
    
    ## - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
    ## Simplest form is cron(1) style schedule.
    ##
    # schedule: "<{ schedule.main }>"
    
    ## - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
    ## Global values.
    ##
    # globals:
    #   global1: "value1"
    #   global2: "value2"
    
    ## - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
    ## Post job actions. If not specified here, the realm level values are used.
    ## Can have list of multiple actions.
    ##
    # on_success:
    #   - action: action-type
    #     param1: ...
    #     param2: ...
    #
    # on_retry:
    #   - action: action-type
    #     param1: ...
    #     param2: ...
    #
    # on_fail:
    #   - action: action-type
    #     param1: ...
    #     param2: ...
    
    ## - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
    ## X-* / x-* vars are ignored by lava but may be useful for other purposes.
    ##
    # X-whatever: "Some value"
    
    type: pkg
    
    ## #############################################################################
    ## Payload is the path to an executable (or list of paths) relative to the
    ## payloads area in S3.
    ##
    payload: "<{ prefix.payload }>/???"
    
    ## #############################################################################
    ## Job parameters
    
    parameters:
      ## ---------------------------------------------------------------------------
      ## Mandatory params
    
      ## The name of the entry point executable in the bundle, relative to the root
      ## of the bundle.  This will be parsed using standard Linux shell lexical
      ## analysis to determine the executable and arguments. Additional arguments
      ## can also be specified with the args parameter.
      ##
      command: "???"
    
      ## ---------------------------------------------------------------------------
      ## Optional params
    
      ## - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
      ## A list of additional arguments for the executable(s) specified in payload.
      ##
      # args:
      #   - "arg1"
      #   - "arg2"
    
      ## - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
      ## Keys are connection labels and the values are conn_id.
      ##
      # connections:
      #     conn1: "conn1_id"
      #     conn2: "conn2_id"
    
      ## - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
      ## A map of additional environment variables for the exe.
      ##
      # env:
      #   env_var1: "value1"
      #   env_var2: "value2"
    
      ## - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
      ## Enable / disable jinja rendering. Default is true. If false, disable Jinja
      ## rendering of the args. Default true.
      ##
      # jinja: true
    
      ## - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
      ## Job timeout. Default is 10 minutes. Values are in the form nnX where nn is
      ## a number and X is s (seconds), m (minutes) or h (hours). If payload is a
      ## list, this is applied to each individual exe.
      ##
      # timeout: "10m"
    
      ## - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
      ## A map of variables injected when the command arguments and environment are
      ## Jinja rendered.
      ##
      # vars:
      #   var1: "value1"
      #   var2: "value2"
    ```

??? "redshift_unload"

    ```yaml
    
    ## #############################################################################
    ## Mandatory fields
    
    enabled: true
    job_id: "<{ prefix.job }>/demo"
    worker: "<{ worker.main }>"
    
    description: "What does this job do?"
    owner: "<{ owner }>"
    
    ## #############################################################################
    ## Optional fields
    ##
    
    ## - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
    ## Dispatcher name
    ##
    ## For scheduled jobs it will be something like...
    # dispatcher: "<{ dispatcher.main }>"
    ##
    ## For non-scheduled jobs it will be omitted
    
    ## - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
    ## enable/disable generation of CloudWatch custom metrics for this job.
    ## If not set, use realm level setting.
    ##
    # cw_metrics: true
    
    ## - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
    ## Log specified information in the events table before the first iteration
    ## commences. Can be a string or an arbitrary object. DON'T LOG SECRETS.
    ##
    # event_log: ...
    
    ## - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
    ## Limit the number of times a single SQS dispatch message can be processed.
    ## Default is 0 which means the limit is determined by SQS queue and worker config.
    ##
    # max_tries: 0
    
    ## - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
    ## Lava internal retry control
    ##
    # iteration_limit: 1
    # iteration_delay: 0s
    
    ## - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
    ## Simplest form is cron(1) style schedule.
    ##
    # schedule: "<{ schedule.main }>"
    
    ## - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
    ## Global values.
    ##
    # globals:
    #   global1: "value1"
    #   global2: "value2"
    
    ## - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
    ## Post job actions. If not specified here, the realm level values are used.
    ## Can have list of multiple actions.
    ##
    # on_success:
    #   - action: action-type
    #     param1: ...
    #     param2: ...
    #
    # on_retry:
    #   - action: action-type
    #     param1: ...
    #     param2: ...
    #
    # on_fail:
    #   - action: action-type
    #     param1: ...
    #     param2: ...
    
    ## - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
    ## X-* / x-* vars are ignored by lava but may be useful for other purposes.
    ##
    # X-whatever: "Some value"
    
    type: redshift_unload
    
    ## #############################################################################
    ## The payload is ignored.
    ##
    payload: "--"
    
    ## #############################################################################
    ## Job parameters
    
    parameters:
      ## ---------------------------------------------------------------------------
      ## Mandatory params
    
      conn_id: "???"
      bucket: "???"
      prefix: "???"
      schema: "???"
    
      # Source relation can be a string or a list
      relation: "???"
    
      ## - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
      ## A list of additional arguments dependent on target DB type
      args:
        - "arg1"
        - "arg2"
    
      ## ---------------------------------------------------------------------------
      ## Optional params
    
      ## - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
      ## S3 connectivity -- either s3_conn_id or s3_iam_role
      ##
      ## The connection ID for AWS S3.
      # s3_conn_id: "???"
      ## The IAM role name used to allow access to the source data in S3.
      # s3_iam_role: "???"
    
      ## - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
      ## Disable bucket security checks. Default is false.
      ##
      # insecure: false
    
      ## - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
      ## Name of the relation to start with when unloading a list of relations. If
      ## not specified, start at the beginning of the list.
      ##
      # start: "relation"
    
      ## - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
      ##  If true, stop when any unload fails otherwise keep moving through the
      ## unload list. Default is true.
      ##
      # stop_on_fail: true
    
      ## - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
      ## A map of variables injected when the S3 target prefix is Jinja rendered.
      ##
      # vars:
      #   var1: "value1"
      #   var2: "value2"
    
      ## - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
      ## An optional WHERE condition for the UNLOAD queries. Do not include the
      ## WHERE keyword.
      ##
      # where: "a where clause common to all source relations"
    ```

??? "sharepoint_get_doc"

    ```yaml
    
    ## #############################################################################
    ## Mandatory fields
    
    enabled: true
    job_id: "<{ prefix.job }>/demo"
    worker: "<{ worker.main }>"
    
    description: "What does this job do?"
    owner: "<{ owner }>"
    
    ## #############################################################################
    ## Optional fields
    ##
    
    ## - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
    ## Dispatcher name
    ##
    ## For scheduled jobs it will be something like...
    # dispatcher: "<{ dispatcher.main }>"
    ##
    ## For non-scheduled jobs it will be omitted
    
    ## - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
    ## enable/disable generation of CloudWatch custom metrics for this job.
    ## If not set, use realm level setting.
    ##
    # cw_metrics: true
    
    ## - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
    ## Log specified information in the events table before the first iteration
    ## commences. Can be a string or an arbitrary object. DON'T LOG SECRETS.
    ##
    # event_log: ...
    
    ## - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
    ## Limit the number of times a single SQS dispatch message can be processed.
    ## Default is 0 which means the limit is determined by SQS queue and worker config.
    ##
    # max_tries: 0
    
    ## - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
    ## Lava internal retry control
    ##
    # iteration_limit: 1
    # iteration_delay: 0s
    
    ## - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
    ## Simplest form is cron(1) style schedule.
    ##
    # schedule: "<{ schedule.main }>"
    
    ## - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
    ## Global values.
    ##
    # globals:
    #   global1: "value1"
    #   global2: "value2"
    
    ## - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
    ## Post job actions. If not specified here, the realm level values are used.
    ## Can have list of multiple actions.
    ##
    # on_success:
    #   - action: action-type
    #     param1: ...
    #     param2: ...
    #
    # on_retry:
    #   - action: action-type
    #     param1: ...
    #     param2: ...
    #
    # on_fail:
    #   - action: action-type
    #     param1: ...
    #     param2: ...
    
    ## - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
    ## X-* / x-* vars are ignored by lava but may be useful for other purposes.
    ##
    # X-whatever: "Some value"
    
    type: sharepoint_get_doc
    
    ## #############################################################################
    ## The payload is ignored.
    ##
    payload: "--"
    
    ## #############################################################################
    ## Job parameters
    
    parameters:
      ## ---------------------------------------------------------------------------
      ## Mandatory params
    
      ## - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
      ## The connection ID for a SharePoint site.
      ##
      conn_id: "???"
    
      ## - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
      ## Source SharePoint library name.
      ##
      library: "???"
    
      ## - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
      ## Source document path in SharePoint. Use POSIX, not DOS, style path names
      ## (i.e. forward slash path separators). Must be an absolute path starting
      ## with /. If a local file and not absolute, it will be relative to the
      ## basedir parameter.
      ##
      path: "???"
    
      ## - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
      ## The destination file name. If it starts with s3:// it is assumed to be an
      ## object in S3, otherwise a local file.
      ##
      file: "???"
    
      ## ---------------------------------------------------------------------------
      ## Optional params
    
      ## - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
      ## If the target file is specified as a relative filename, it will be treated
      ## as relative to the specified directory. Defaults to the lava temporary
      ## directory for the job.
      ##
      # basedir: "dir"
    
      ## - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
      ## AWS KMS encryption key to use when uploading to AWS S3.
      ##
      # kms_key_id: "alias/whatever"
    
      ## - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
      ## Enable / disable jinja rendering. Default is true. If false, disable Jinja
      ## rendering of the args. Default true.
      ##
      # jinja: true
    
      ## - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
      ## A map of variables injected when the command arguments and environment are
      ## Jinja rendered.
      ##
      # vars:
      #   var1: "value1"
      #   var2: "value2"
    ```

??? "sharepoint_get_list"

    ```yaml
    
    ## #############################################################################
    ## Mandatory fields
    
    enabled: true
    job_id: "<{ prefix.job }>/demo"
    worker: "<{ worker.main }>"
    
    description: "What does this job do?"
    owner: "<{ owner }>"
    
    ## #############################################################################
    ## Optional fields
    ##
    
    ## - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
    ## Dispatcher name
    ##
    ## For scheduled jobs it will be something like...
    # dispatcher: "<{ dispatcher.main }>"
    ##
    ## For non-scheduled jobs it will be omitted
    
    ## - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
    ## enable/disable generation of CloudWatch custom metrics for this job.
    ## If not set, use realm level setting.
    ##
    # cw_metrics: true
    
    ## - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
    ## Log specified information in the events table before the first iteration
    ## commences. Can be a string or an arbitrary object. DON'T LOG SECRETS.
    ##
    # event_log: ...
    
    ## - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
    ## Limit the number of times a single SQS dispatch message can be processed.
    ## Default is 0 which means the limit is determined by SQS queue and worker config.
    ##
    # max_tries: 0
    
    ## - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
    ## Lava internal retry control
    ##
    # iteration_limit: 1
    # iteration_delay: 0s
    
    ## - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
    ## Simplest form is cron(1) style schedule.
    ##
    # schedule: "<{ schedule.main }>"
    
    ## - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
    ## Global values.
    ##
    # globals:
    #   global1: "value1"
    #   global2: "value2"
    
    ## - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
    ## Post job actions. If not specified here, the realm level values are used.
    ## Can have list of multiple actions.
    ##
    # on_success:
    #   - action: action-type
    #     param1: ...
    #     param2: ...
    #
    # on_retry:
    #   - action: action-type
    #     param1: ...
    #     param2: ...
    #
    # on_fail:
    #   - action: action-type
    #     param1: ...
    #     param2: ...
    
    ## - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
    ## X-* / x-* vars are ignored by lava but may be useful for other purposes.
    ##
    # X-whatever: "Some value"
    
    type: sharepoint_get_list
    
    ## #############################################################################
    ## The payload is ignored.
    ##
    payload: "--"
    
    ## #############################################################################
    ## Job parameters
    
    parameters:
      ## ---------------------------------------------------------------------------
      ## Mandatory params
    
      ## - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
      ## The connection ID for a SharePoint site.
      ##
      conn_id: "???"
    
      ## - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
      ## The destination file name. If it starts with s3:// it is assumed to be an
      ## object in S3, otherwise a local file.
      ##
      file: "???"
    
      ## - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
      ## Name of the SharePoint list. It must already exist in SharePoint.
      ##
      list: "???"
    
      ## ---------------------------------------------------------------------------
      ## Optional params
    
      ## - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
      ## If the target file is specified as a relative filename, it will be treated
      ## as relative to the specified directory. Defaults to the lava temporary
      ## directory for the job.
      ##
      # basedir: "dir"
    
      ## - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
      ## A comma separated list of column names. If specified, then only columns
      ## listed are extracted (in addition to any specified system_columns).
      ##
      # data_columns: "col1,col2,col3"
    
      ## - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
      ## Column delimiter. Default is pipe (|)
      ##
      # delimiter: "|"
    
      ## - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
      ## As for csv.writer.
      ##
      # escapechar: null
    
      ## - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
      ## If true, include a header line containing column names
      ##
      # header: true
    
      ## - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
      ## Enable / disable jinja rendering. Default is true. If false, disable Jinja
      ## rendering of the args. Default true.
      ##
      # jinja: true
    
      ## - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
      ## AWS KMS encryption key to use when uploading to AWS S3.
      ##
      # kms_key_id: "alias/whatever"
    
      ## - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
      ## As for csv.writer. Default "
      ##
      # quotechar: '"'
    
      ## - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
      ## As for csv.writer QUOTE_* parameters (without the QUOTE_ prefix). Default
      ## minimal (i.e. QUOTE_MINIMAL).
      ##
      # quoting: "minimal"
    
      ## - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
      ## A comma separated list of system columns to retrieve in addition to the
      ## data columns. Unless specified, only data columns are retrieved.
      ##
      # system_columns: "Author,Created"
    
      ## - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
      ## A map of variables injected when the parameters are Jinja rendered.
      ##
      # vars:
      #   var1: "value1"
      #   var2: "value2"
    ```

??? "sharepoint_get_multi_doc"

    ```yaml
    
    ## #############################################################################
    ## Mandatory fields
    
    enabled: true
    job_id: "<{ prefix.job }>/demo"
    worker: "<{ worker.main }>"
    
    description: "What does this job do?"
    owner: "<{ owner }>"
    
    ## #############################################################################
    ## Optional fields
    ##
    
    ## - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
    ## Dispatcher name
    ##
    ## For scheduled jobs it will be something like...
    # dispatcher: "<{ dispatcher.main }>"
    ##
    ## For non-scheduled jobs it will be omitted
    
    ## - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
    ## enable/disable generation of CloudWatch custom metrics for this job.
    ## If not set, use realm level setting.
    ##
    # cw_metrics: true
    
    ## - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
    ## Log specified information in the events table before the first iteration
    ## commences. Can be a string or an arbitrary object. DON'T LOG SECRETS.
    ##
    # event_log: ...
    
    ## - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
    ## Limit the number of times a single SQS dispatch message can be processed.
    ## Default is 0 which means the limit is determined by SQS queue and worker config.
    ##
    # max_tries: 0
    
    ## - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
    ## Lava internal retry control
    ##
    # iteration_limit: 1
    # iteration_delay: 0s
    
    ## - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
    ## Simplest form is cron(1) style schedule.
    ##
    # schedule: "<{ schedule.main }>"
    
    ## - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
    ## Global values.
    ##
    # globals:
    #   global1: "value1"
    #   global2: "value2"
    
    ## - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
    ## Post job actions. If not specified here, the realm level values are used.
    ## Can have list of multiple actions.
    ##
    # on_success:
    #   - action: action-type
    #     param1: ...
    #     param2: ...
    #
    # on_retry:
    #   - action: action-type
    #     param1: ...
    #     param2: ...
    #
    # on_fail:
    #   - action: action-type
    #     param1: ...
    #     param2: ...
    
    ## - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
    ## X-* / x-* vars are ignored by lava but may be useful for other purposes.
    ##
    # X-whatever: "Some value"
    
    type: sharepoint_get_multi_doc
    
    ## #############################################################################
    ## The payload is ignored.
    ##
    payload: "--"
    
    ## #############################################################################
    ## Job parameters
    
    parameters:
      ## ---------------------------------------------------------------------------
      ## Mandatory params
    
      ## - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
      ## The connection ID for a SharePoint site.
      ##
      conn_id: "???"
    
      ## - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
      ## Source SharePoint library name.
      ##
      library: "???"
    
      ## - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
      ## Source document path in SharePoint. Use POSIX, not DOS, style path names
      ## (i.e. forward slash path separators). Must be an absolute path starting
      ## with /. If a local file and not absolute, it will be relative to the
      ## basedir parameter.
      ##
      path: "???"
    
      ## - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
      ## The destination path. If it starts with s3:// it is assumed to be an
      ## object in S3 with base prefix to store files, otherwise a local directory.
      ##
      outpath: "???"
    
      ## ---------------------------------------------------------------------------
      ## Optional params
    
      ## - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
      ## The glob to filter on in source SharePoint path. Only downloads files
      ## matching this glob direct in the path, and doesn't resurse down folders.
      ##
      # glob: "*.csv"
    
      ## - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
      ## If the target file is specified as a relative filename, it will be treated
      ## as relative to the specified directory. Defaults to the lava temporary
      ## directory for the job.
      ##
      # basedir: "dir"
    
      ## - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
      ## AWS KMS encryption key to use when uploading to AWS S3.
      ##
      # kms_key_id: "alias/whatever"
    
      ## - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
      ## Enable / disable jinja rendering. Default is true. If false, disable Jinja
      ## rendering of the args. Default true.
      ##
      # jinja: true
    
      ## - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
      ## A map of variables injected when the command arguments and environment are
      ## Jinja rendered.
      ##
      # vars:
      #   var1: "value1"
      #   var2: "value2"
    ```

??? "sharepoint_put_doc"

    ```yaml
    
    ## #############################################################################
    ## Mandatory fields
    
    enabled: true
    job_id: "<{ prefix.job }>/demo"
    worker: "<{ worker.main }>"
    
    description: "What does this job do?"
    owner: "<{ owner }>"
    
    ## #############################################################################
    ## Optional fields
    ##
    
    ## - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
    ## Dispatcher name
    ##
    ## For scheduled jobs it will be something like...
    # dispatcher: "<{ dispatcher.main }>"
    ##
    ## For non-scheduled jobs it will be omitted
    
    ## - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
    ## enable/disable generation of CloudWatch custom metrics for this job.
    ## If not set, use realm level setting.
    ##
    # cw_metrics: true
    
    ## - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
    ## Log specified information in the events table before the first iteration
    ## commences. Can be a string or an arbitrary object. DON'T LOG SECRETS.
    ##
    # event_log: ...
    
    ## - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
    ## Limit the number of times a single SQS dispatch message can be processed.
    ## Default is 0 which means the limit is determined by SQS queue and worker config.
    ##
    # max_tries: 0
    
    ## - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
    ## Lava internal retry control
    ##
    # iteration_limit: 1
    # iteration_delay: 0s
    
    ## - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
    ## Simplest form is cron(1) style schedule.
    ##
    # schedule: "<{ schedule.main }>"
    
    ## - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
    ## Global values.
    ##
    # globals:
    #   global1: "value1"
    #   global2: "value2"
    
    ## - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
    ## Post job actions. If not specified here, the realm level values are used.
    ## Can have list of multiple actions.
    ##
    # on_success:
    #   - action: action-type
    #     param1: ...
    #     param2: ...
    #
    # on_retry:
    #   - action: action-type
    #     param1: ...
    #     param2: ...
    #
    # on_fail:
    #   - action: action-type
    #     param1: ...
    #     param2: ...
    
    ## - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
    ## X-* / x-* vars are ignored by lava but may be useful for other purposes.
    ##
    # X-whatever: "Some value"
    
    type: sharepoint_put_doc
    
    ## #############################################################################
    ## The payload is ignored.
    ##
    payload: "--"
    
    ## #############################################################################
    ## Job parameters
    
    parameters:
      ## ---------------------------------------------------------------------------
      ## Mandatory params
    
      ## - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
      ## The connection ID for a SharePoint site.
      ##
      conn_id: "???"
    
      ## - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
      ## Source SharePoint library name.
      ##
      library: "???"
    
      ## - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
      ## Source document path in SharePoint. Use POSIX, not DOS, style path names
      ## (i.e. forward slash path separators). Must be an absolute path starting
      ## with /. If a local file and not absolute, it will be relative to the
      ## basedir parameter.
      ##
      path: "???"
    
      ## - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
      ## The destination file name. If it starts with s3:// it is assumed to be an
      ## object in S3, otherwise a local file.
      ##
      file: "???"
    
      ## ---------------------------------------------------------------------------
      ## Optional params
    
      ## - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
      ##  A title for the document.
      ##
      # title: "Document title"
    
      ## - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
      ## If the target file is specified as a relative filename, it will be treated
      ## as relative to the specified directory. Defaults to the lava temporary
      ## directory for the job.
      ##
      # basedir: "dir"
    
      ## - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
      ## AWS KMS encryption key to use when uploading to AWS S3.
      ##
      # kms_key_id: "alias/whatever"
    
      ## - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
      ## Enable / disable jinja rendering. Default is true. If false, disable Jinja
      ## rendering of the args. Default true.
      ##
      # jinja: true
    
      ## - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
      ## A map of variables injected when the command arguments and environment are
      ## Jinja rendered.
      ##
      # vars:
      #   var1: "value1"
      #   var2: "value2"
    ```

??? "sharepoint_put_list"

    ```yaml
    
    ## #############################################################################
    ## Mandatory fields
    
    enabled: true
    job_id: "<{ prefix.job }>/demo"
    worker: "<{ worker.main }>"
    
    description: "What does this job do?"
    owner: "<{ owner }>"
    
    ## #############################################################################
    ## Optional fields
    ##
    
    ## - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
    ## Dispatcher name
    ##
    ## For scheduled jobs it will be something like...
    # dispatcher: "<{ dispatcher.main }>"
    ##
    ## For non-scheduled jobs it will be omitted
    
    ## - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
    ## enable/disable generation of CloudWatch custom metrics for this job.
    ## If not set, use realm level setting.
    ##
    # cw_metrics: true
    
    ## - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
    ## Log specified information in the events table before the first iteration
    ## commences. Can be a string or an arbitrary object. DON'T LOG SECRETS.
    ##
    # event_log: ...
    
    ## - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
    ## Limit the number of times a single SQS dispatch message can be processed.
    ## Default is 0 which means the limit is determined by SQS queue and worker config.
    ##
    # max_tries: 0
    
    ## - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
    ## Lava internal retry control
    ##
    # iteration_limit: 1
    # iteration_delay: 0s
    
    ## - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
    ## Simplest form is cron(1) style schedule.
    ##
    # schedule: "<{ schedule.main }>"
    
    ## - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
    ## Global values.
    ##
    # globals:
    #   global1: "value1"
    #   global2: "value2"
    
    ## - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
    ## Post job actions. If not specified here, the realm level values are used.
    ## Can have list of multiple actions.
    ##
    # on_success:
    #   - action: action-type
    #     param1: ...
    #     param2: ...
    #
    # on_retry:
    #   - action: action-type
    #     param1: ...
    #     param2: ...
    #
    # on_fail:
    #   - action: action-type
    #     param1: ...
    #     param2: ...
    
    ## - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
    ## X-* / x-* vars are ignored by lava but may be useful for other purposes.
    ##
    # X-whatever: "Some value"
    
    type: sharepoint_get_list
    
    ## #############################################################################
    ## The payload is ignored.
    ##
    payload: "--"
    
    ## #############################################################################
    ## Job parameters
    
    parameters:
      ## ---------------------------------------------------------------------------
      ## Mandatory params
    
      ## - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
      ## The connection ID for a SharePoint site.
      ##
      conn_id: "???"
    
      ## - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
      ## The source file name. If it starts with s3:// it is assumed to be an
      ## object in S3, otherwise a local file.
      ##
      file: "???"
    
      ## - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
      ## Name of the SharePoint list. It must already exist in SharePoint.
      ##
      list: "???"
    
      ## ---------------------------------------------------------------------------
      ## Optional params
    
      ## - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
      ## If the source file is specified as a relative filename, it will be treated
      ## as relative to the specified directory. Defaults to the lava temporary
      ## directory for the job.
      ##
      # basedir: "dir"
    
      ## - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
      ## A comma separated list of column names. If specified, then only columns
      ## listed are modified.
      ##
      # data_columns: "col1,col2,col3"
    
      ## - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
      ## Column delimiter. Default is pipe (|)
      ##
      # delimiter: "|"
    
      ## - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
      ## As for csv.reader. Default false.
      ##
      # doubleqoute: false
    
      ## - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
      ## If true and there are columns in the source file that are not in the
      ## SharePoint list, raise an error. If false, the extra columns are silently
      ## ignored. Default false.
      ##
      # error_missing: false
    
      ## - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
      ## As for csv.reader.
      ##
      # escapechar: null
    
      ## - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
      ## Enable / disable jinja rendering. Default is true. If false, disable Jinja
      ## rendering of the args. Default true.
      ##
      # jinja: true
    
      ## - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
      ## Put mode. Must be append, delete, replace or update. Default is append.
      ##
      # mode: "append"
    
      ## - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
      ## As for csv.reader. Default "
      ##
      # quotechar: '"'
    
      ## - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
      ## As for csv.reader QUOTE_* parameters (without the QUOTE_ prefix). Default
      ## minimal (i.e. QUOTE_MINIMAL).
      ##
      # quoting: "minimal"
    
      ## - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
      ## A map of variables injected when the parameters are Jinja rendered.
      ##
      # vars:
      #   var1: "value1"
      #   var2: "value2"
    ```

??? "smb_get"

    ```yaml
    
    ## #############################################################################
    ## Mandatory fields
    
    enabled: true
    job_id: "<{ prefix.job }>/demo"
    worker: "<{ worker.main }>"
    
    description: "What does this job do?"
    owner: "<{ owner }>"
    
    ## #############################################################################
    ## Optional fields
    ##
    
    ## - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
    ## Dispatcher name
    ##
    ## For scheduled jobs it will be something like...
    # dispatcher: "<{ dispatcher.main }>"
    ##
    ## For non-scheduled jobs it will be omitted
    
    ## - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
    ## enable/disable generation of CloudWatch custom metrics for this job.
    ## If not set, use realm level setting.
    ##
    # cw_metrics: true
    
    ## - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
    ## Log specified information in the events table before the first iteration
    ## commences. Can be a string or an arbitrary object. DON'T LOG SECRETS.
    ##
    # event_log: ...
    
    ## - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
    ## Limit the number of times a single SQS dispatch message can be processed.
    ## Default is 0 which means the limit is determined by SQS queue and worker config.
    ##
    # max_tries: 0
    
    ## - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
    ## Lava internal retry control
    ##
    # iteration_limit: 1
    # iteration_delay: 0s
    
    ## - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
    ## Simplest form is cron(1) style schedule.
    ##
    # schedule: "<{ schedule.main }>"
    
    ## - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
    ## Global values.
    ##
    # globals:
    #   global1: "value1"
    #   global2: "value2"
    
    ## - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
    ## Post job actions. If not specified here, the realm level values are used.
    ## Can have list of multiple actions.
    ##
    # on_success:
    #   - action: action-type
    #     param1: ...
    #     param2: ...
    #
    # on_retry:
    #   - action: action-type
    #     param1: ...
    #     param2: ...
    #
    # on_fail:
    #   - action: action-type
    #     param1: ...
    #     param2: ...
    
    ## - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
    ## X-* / x-* vars are ignored by lava but may be useful for other purposes.
    ##
    # X-whatever: "Some value"
    
    type: smb_get
    
    ## #############################################################################
    ## The payload is ignored.
    ##
    payload: "--"
    
    ## #############################################################################
    ## Job parameters
    
    parameters:
      ## ---------------------------------------------------------------------------
      ## Mandatory params
    
      ## - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
      ## The connection ID for a SMB share.
      ##
      conn_id: "???"
    
      ## - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
      ## The destination file name. If it starts with s3:// it is assumed to be an
      ## object in S3, otherwise a local file.
      ##
      file: "???"
    
      ## - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
      ## The source file path on the SMB file share. Use POSIX, not DOS, style path
      ## names (i.e. forward slash path separators). This value is Jinja rendered.
      ##
      path: "???"
    
      ## - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
      ## The name of the file share.
      ##
      share: "???"
    
      ## ---------------------------------------------------------------------------
      ## Optional params
    
      ## - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
      ## If the target file is specified as a relative filename, it will be treated
      ## as relative to the specified directory. Defaults to the lava temporary
      ## directory for the job.
      ##
      # basedir: "dir"
    
      ## - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
      ## Enable / disable jinja rendering. Default is true. If false, disable Jinja
      ## rendering of the args. Default true.
      ##
      # jinja: true
    
      ## - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
      ## AWS KMS encryption key to use when uploading to AWS S3.
      ##
      # kms_key_id: "alias/whatever"
    
      ## - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
      ## A map of variables injected when the command arguments and environment are
      ## Jinja rendered.
      ##
      # vars:
      #   var1: "value1"
      #   var2: "value2"
    ```

??? "smb_put"

    ```yaml
    
    ## #############################################################################
    ## Mandatory fields
    
    enabled: true
    job_id: "<{ prefix.job }>/demo"
    worker: "<{ worker.main }>"
    
    description: "What does this job do?"
    owner: "<{ owner }>"
    
    ## #############################################################################
    ## Optional fields
    ##
    
    ## - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
    ## Dispatcher name
    ##
    ## For scheduled jobs it will be something like...
    # dispatcher: "<{ dispatcher.main }>"
    ##
    ## For non-scheduled jobs it will be omitted
    
    ## - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
    ## enable/disable generation of CloudWatch custom metrics for this job.
    ## If not set, use realm level setting.
    ##
    # cw_metrics: true
    
    ## - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
    ## Log specified information in the events table before the first iteration
    ## commences. Can be a string or an arbitrary object. DON'T LOG SECRETS.
    ##
    # event_log: ...
    
    ## - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
    ## Limit the number of times a single SQS dispatch message can be processed.
    ## Default is 0 which means the limit is determined by SQS queue and worker config.
    ##
    # max_tries: 0
    
    ## - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
    ## Lava internal retry control
    ##
    # iteration_limit: 1
    # iteration_delay: 0s
    
    ## - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
    ## Simplest form is cron(1) style schedule.
    ##
    # schedule: "<{ schedule.main }>"
    
    ## - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
    ## Global values.
    ##
    # globals:
    #   global1: "value1"
    #   global2: "value2"
    
    ## - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
    ## Post job actions. If not specified here, the realm level values are used.
    ## Can have list of multiple actions.
    ##
    # on_success:
    #   - action: action-type
    #     param1: ...
    #     param2: ...
    #
    # on_retry:
    #   - action: action-type
    #     param1: ...
    #     param2: ...
    #
    # on_fail:
    #   - action: action-type
    #     param1: ...
    #     param2: ...
    
    ## - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
    ## X-* / x-* vars are ignored by lava but may be useful for other purposes.
    ##
    # X-whatever: "Some value"
    
    type: smb_put
    
    ## #############################################################################
    ## The payload is ignored.
    ##
    payload: "--"
    
    ## #############################################################################
    ## Job parameters
    
    parameters:
      ## ---------------------------------------------------------------------------
      ## Mandatory params
    
      ## - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
      ## The connection ID for a SMB file share.
      ##
      conn_id: "???"
    
      ## - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
      ## The source file name. If it starts with s3:// it is assumed to be an
      ## object in S3, otherwise a local file.
      ##
      file: "???"
    
      ## - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
      ## The destination file path on the SMB file share. Use POSIX, not DOS, style
      ## path names (i.e. forward slash path separators). This value is Jinja
      ## rendered.
      ##
      path: "???"
    
      ## - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
      ## The name of the file share.
      ##
      share: "???"
    
      ## ---------------------------------------------------------------------------
      ## Optional params
    
      ## - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
      ## If the source file is specified as a relative filename, it will be treated
      ## as relative to the specified directory. Defaults to the lava temporary
      ## directory for the job.
      ##
      # basedir: "dir"
    
      ## - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
      ## If true, the target directory, including parent directories, will be
      ## created if it doesn’t exist. Default is false
      ##
      # create_dirs: false
    
      ## - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
      ## Enable / disable jinja rendering. Default is true. If false, disable Jinja
      ## rendering of the args. Default true.
      ##
      # jinja: true
    
      ## - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
      ## A map of variables injected when the command arguments and environment are
      ## Jinja rendered.
      ##
      # vars:
      #   var1: "value1"
      #   var2: "value2"
    ```

??? "sql"

    ```yaml
    
    ## #############################################################################
    ## Mandatory fields
    
    enabled: true
    job_id: "<{ prefix.job }>/demo"
    worker: "<{ worker.main }>"
    
    description: "What does this job do?"
    owner: "<{ owner }>"
    
    ## #############################################################################
    ## Optional fields
    ##
    
    ## - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
    ## Dispatcher name
    ##
    ## For scheduled jobs it will be something like...
    # dispatcher: "<{ dispatcher.main }>"
    ##
    ## For non-scheduled jobs it will be omitted
    
    ## - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
    ## enable/disable generation of CloudWatch custom metrics for this job.
    ## If not set, use realm level setting.
    ##
    # cw_metrics: true
    
    ## - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
    ## Log specified information in the events table before the first iteration
    ## commences. Can be a string or an arbitrary object. DON'T LOG SECRETS.
    ##
    # event_log: ...
    
    ## - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
    ## Limit the number of times a single SQS dispatch message can be processed.
    ## Default is 0 which means the limit is determined by SQS queue and worker config.
    ##
    # max_tries: 0
    
    ## - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
    ## Lava internal retry control
    ##
    # iteration_limit: 1
    # iteration_delay: 0s
    
    ## - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
    ## Simplest form is cron(1) style schedule.
    ##
    # schedule: "<{ schedule.main }>"
    
    ## - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
    ## Global values.
    ##
    # globals:
    #   global1: "value1"
    #   global2: "value2"
    
    ## - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
    ## Post job actions. If not specified here, the realm level values are used.
    ## Can have list of multiple actions.
    ##
    # on_success:
    #   - action: action-type
    #     param1: ...
    #     param2: ...
    #
    # on_retry:
    #   - action: action-type
    #     param1: ...
    #     param2: ...
    #
    # on_fail:
    #   - action: action-type
    #     param1: ...
    #     param2: ...
    
    ## - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
    ## X-* / x-* vars are ignored by lava but may be useful for other purposes.
    ##
    # X-whatever: "Some value"
    
    type: sql
    
    ## #############################################################################
    ## The payload is a location in S3 relative to the s3_payloads area. It can be
    ## either an object key, in which case a single file is downloaded, or a prefix
    ## ending in /, in which case all files under that prefix will be downloaded and
    ## run in lexicographic order.
    ##
    payload: "???"
    
    ## #############################################################################
    ## Job parameters
    
    parameters:
      ## ---------------------------------------------------------------------------
      ## Mandatory params
    
      ## - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
      ## The connection ID for the database.
      ##
      conn_id: "???"
    
      ## ---------------------------------------------------------------------------
      ## Optional params
    
      ## - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
      ## Fetch this many rows at a time.
      ##
      # batch_size: 1000
    
      ## - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
      ## Column delimiter. Default is pipe (|)
      ##
      # delimiter: "|"
    
      ## - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
      ## As for csv.writer. Default is excel.
      ##
      # dialect: "excel"
    
      ## - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
      ## As for csv.writer. Default false.
      ##
      # doubleqoute: false
    
      ## - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
      ## As for csv.writer.
      ##
      # escapechar: null
    
      ## - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
      ## Add a header for SELECT outputs if true. Default is false.
      ##
      # header: false
    
      ## - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
      ## Enable / disable jinja rendering. Default is true. If false, disable Jinja
      ## rendering of the args. Default true.
      ##
      # jinja: true
    
      ## - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
      ## As for csv.writer. Default "
      ##
      # quotechar: '"'
    
      ## - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
      ## As for csv.writer QUOTE_* parameters (without the QUOTE_ prefix). Default
      ## minimal (i.e. QUOTE_MINIMAL).
      ##
      # quoting: "minimal"
    
      ## - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
      ## Suppress splitting of payload files into individual SQL statements.
      ## Default: false (i.e. allow splitting).
      ##
      # raw: false
    
      ## - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
      ## If true, auto-commit is disabled and the sequence of SQLs is run within a
      ## transaction. If false, auto-commit is enabled. Default false.
      ##
      # transaction: false
    
      ## - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
      ## A map of variables injected when the SQL is Jinja rendered.
      ##
      # vars:
      #   var1: "value1"
      #   var2: "value2"
    ```

??? "sqlc"

    ```yaml
    
    ## #############################################################################
    ## Mandatory fields
    
    enabled: true
    job_id: "<{ prefix.job }>/demo"
    worker: "<{ worker.main }>"
    
    description: "What does this job do?"
    owner: "<{ owner }>"
    
    ## #############################################################################
    ## Optional fields
    ##
    
    ## - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
    ## Dispatcher name
    ##
    ## For scheduled jobs it will be something like...
    # dispatcher: "<{ dispatcher.main }>"
    ##
    ## For non-scheduled jobs it will be omitted
    
    ## - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
    ## enable/disable generation of CloudWatch custom metrics for this job.
    ## If not set, use realm level setting.
    ##
    # cw_metrics: true
    
    ## - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
    ## Log specified information in the events table before the first iteration
    ## commences. Can be a string or an arbitrary object. DON'T LOG SECRETS.
    ##
    # event_log: ...
    
    ## - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
    ## Limit the number of times a single SQS dispatch message can be processed.
    ## Default is 0 which means the limit is determined by SQS queue and worker config.
    ##
    # max_tries: 0
    
    ## - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
    ## Lava internal retry control
    ##
    # iteration_limit: 1
    # iteration_delay: 0s
    
    ## - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
    ## Simplest form is cron(1) style schedule.
    ##
    # schedule: "<{ schedule.main }>"
    
    ## - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
    ## Global values.
    ##
    # globals:
    #   global1: "value1"
    #   global2: "value2"
    
    ## - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
    ## Post job actions. If not specified here, the realm level values are used.
    ## Can have list of multiple actions.
    ##
    # on_success:
    #   - action: action-type
    #     param1: ...
    #     param2: ...
    #
    # on_retry:
    #   - action: action-type
    #     param1: ...
    #     param2: ...
    #
    # on_fail:
    #   - action: action-type
    #     param1: ...
    #     param2: ...
    
    ## - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
    ## X-* / x-* vars are ignored by lava but may be useful for other purposes.
    ##
    # X-whatever: "Some value"
    
    type: sqlc
    
    ## #############################################################################
    ## The payload is a location in S3 relative to the s3_payloads area. It can be
    ## either an object key, in which case a single file is downloaded, or a prefix
    ## ending in /, in which case all files under that prefix will be downloaded and
    ## run in lexicographic order.
    ##
    payload: "???"
    
    ## #############################################################################
    ## Job parameters
    
    parameters:
      ## ---------------------------------------------------------------------------
      ## Mandatory params
    
      ## - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
      ## The connection ID for the database.
      ##
      conn_id: "???"
    
      ## ---------------------------------------------------------------------------
      ## Optional params
    
      ## - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
      ## A list of zero or more additional arguments provided to the database client.
      ## These are necessarily specific to the database type and underlying database
      ## client.
      ##
      # args:
      #   - "arg1"
      #   - "arg2"
    
      ## - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
      ## Enable / disable jinja rendering. Default is true. If false, disable Jinja
      ## rendering of the args. Default true.
      ##
      # jinja: true
    
      ## - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
      ## Timeout for each job component script. Default is 10 minutes. Values are in
      ## the form nnX where nn is a number and X is s (seconds), m (minutes) or
      ## h (hours).
      ##
      # timeout: "10m"
    
      ## - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
      ## A map of variables injected when the SQL is Jinja rendered.
      ##
      # vars:
      #   var1: "value1"
      #   var2: "value2"
    ```

??? "sqli"

    ```yaml
    
    ## #############################################################################
    ## Mandatory fields
    
    enabled: true
    job_id: "<{ prefix.job }>/demo"
    worker: "<{ worker.main }>"
    
    description: "What does this job do?"
    owner: "<{ owner }>"
    
    ## #############################################################################
    ## Optional fields
    ##
    
    ## - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
    ## Dispatcher name
    ##
    ## For scheduled jobs it will be something like...
    # dispatcher: "<{ dispatcher.main }>"
    ##
    ## For non-scheduled jobs it will be omitted
    
    ## - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
    ## enable/disable generation of CloudWatch custom metrics for this job.
    ## If not set, use realm level setting.
    ##
    # cw_metrics: true
    
    ## - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
    ## Log specified information in the events table before the first iteration
    ## commences. Can be a string or an arbitrary object. DON'T LOG SECRETS.
    ##
    # event_log: ...
    
    ## - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
    ## Limit the number of times a single SQS dispatch message can be processed.
    ## Default is 0 which means the limit is determined by SQS queue and worker config.
    ##
    # max_tries: 0
    
    ## - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
    ## Lava internal retry control
    ##
    # iteration_limit: 1
    # iteration_delay: 0s
    
    ## - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
    ## Simplest form is cron(1) style schedule.
    ##
    # schedule: "<{ schedule.main }>"
    
    ## - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
    ## Global values.
    ##
    # globals:
    #   global1: "value1"
    #   global2: "value2"
    
    ## - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
    ## Post job actions. If not specified here, the realm level values are used.
    ## Can have list of multiple actions.
    ##
    # on_success:
    #   - action: action-type
    #     param1: ...
    #     param2: ...
    #
    # on_retry:
    #   - action: action-type
    #     param1: ...
    #     param2: ...
    #
    # on_fail:
    #   - action: action-type
    #     param1: ...
    #     param2: ...
    
    ## - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
    ## X-* / x-* vars are ignored by lava but may be useful for other purposes.
    ##
    # X-whatever: "Some value"
    
    type: sqli
    
    ## #############################################################################
    ## The payload is an SQL statement or a list of statements. The YAML multi-line
    ## syntax can help here. https://yaml-multiline.info
    ##
    payload: |
      SELECT *
      FROM my_schema.my_table;
    
    ## #############################################################################
    ## Job parameters
    
    parameters:
      ## ---------------------------------------------------------------------------
      ## Mandatory params
    
      ## - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
      ## The connection ID for the database.
      ##
      conn_id: "???"
    
      ## ---------------------------------------------------------------------------
      ## Optional params
    
      ## - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
      ## Fetch this many rows at a time.
      ##
      # batch_size: 1000
    
      ## - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
      ## Column delimiter. Default is pipe (|)
      ##
      # delimiter: "|"
    
      ## - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
      ## As for csv.writer. Default is excel.
      ##
      # dialect: "excel"
    
      ## - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
      ## As for csv.writer. Default false.
      ##
      # doubleqoute: false
    
      ## - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
      ## As for csv.writer.
      ##
      # escapechar: null
    
      ## - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
      ## Add a header for SELECT outputs if true. Default is false.
      ##
      # header: false
    
      ## - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
      ## Enable / disable jinja rendering. Default is true. If false, disable Jinja
      ## rendering of the args. Default true.
      ##
      # jinja: true
    
      ## - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
      ## As for csv.writer. Default "
      ##
      # quotechar: '"'
    
      ## - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
      ## As for csv.writer QUOTE_* parameters (without the QUOTE_ prefix). Default
      ## minimal (i.e. QUOTE_MINIMAL).
      ##
      # quoting: "minimal"
    
      ## - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
      ## Suppress splitting of payload files into individual SQL statements.
      ## Default: false (i.e. allow splitting).
      ##
      # raw: false
    
      ## - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
      ## If true, auto-commit is disabled and the sequence of SQLs is run within a
      ## transaction. If false, auto-commit is enabled. Default false.
      ##
      # transaction: false
    
      ## - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
      ## A map of variables injected when the SQL is Jinja rendered.
      ##
      # vars:
      #   var1: "value1"
      #   var2: "value2"
    ```

??? "sqlv"

    ```yaml
    
    ## #############################################################################
    ## Mandatory fields
    
    enabled: true
    job_id: "<{ prefix.job }>/demo"
    worker: "<{ worker.main }>"
    
    description: "What does this job do?"
    owner: "<{ owner }>"
    
    ## #############################################################################
    ## Optional fields
    ##
    
    ## - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
    ## Dispatcher name
    ##
    ## For scheduled jobs it will be something like...
    # dispatcher: "<{ dispatcher.main }>"
    ##
    ## For non-scheduled jobs it will be omitted
    
    ## - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
    ## enable/disable generation of CloudWatch custom metrics for this job.
    ## If not set, use realm level setting.
    ##
    # cw_metrics: true
    
    ## - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
    ## Log specified information in the events table before the first iteration
    ## commences. Can be a string or an arbitrary object. DON'T LOG SECRETS.
    ##
    # event_log: ...
    
    ## - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
    ## Limit the number of times a single SQS dispatch message can be processed.
    ## Default is 0 which means the limit is determined by SQS queue and worker config.
    ##
    # max_tries: 0
    
    ## - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
    ## Lava internal retry control
    ##
    # iteration_limit: 1
    # iteration_delay: 0s
    
    ## - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
    ## Simplest form is cron(1) style schedule.
    ##
    # schedule: "<{ schedule.main }>"
    
    ## - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
    ## Global values.
    ##
    # globals:
    #   global1: "value1"
    #   global2: "value2"
    
    ## - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
    ## Post job actions. If not specified here, the realm level values are used.
    ## Can have list of multiple actions.
    ##
    # on_success:
    #   - action: action-type
    #     param1: ...
    #     param2: ...
    #
    # on_retry:
    #   - action: action-type
    #     param1: ...
    #     param2: ...
    #
    # on_fail:
    #   - action: action-type
    #     param1: ...
    #     param2: ...
    
    ## - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
    ## X-* / x-* vars are ignored by lava but may be useful for other purposes.
    ##
    # X-whatever: "Some value"
    
    type: sqlv
    
    ## #############################################################################
    ## The payload is a location in S3 relative to the s3_payloads area. It can be
    ## either an object key, in which case a single file is downloaded, or a prefix
    ## ending in /, in which case all files under that prefix will be downloaded and
    ## run in lexicographic order.
    ##
    payload: "???"
    
    ## #############################################################################
    ## Job parameters
    
    parameters:
      ## ---------------------------------------------------------------------------
      ## Mandatory params
    
      ## - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
      ## The connection ID for the database.
      ##
      conn_id: "???"
    
      ## ---------------------------------------------------------------------------
      ## Optional params
    
      ## - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
      ## Fetch this many rows at a time.
      ##
      # batch_size: 1024
    
      ## - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
      ## Column delimiter. Default is pipe (|)
      ##
      # delimiter: "|"
    
      ## - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
      ## As for csv.writer. Default is excel.
      ##
      # dialect: "excel"
    
      ## - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
      ## As for csv.writer. Default false.
      ##
      # doubleqoute: false
    
      ## - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
      ## As for csv.writer.
      ##
      # escapechar: null
    
      ## - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
      ## Output format for SELECTs
      ##
      # format: csv
    
      ## - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
      ## Add a header for SELECT outputs if true. Default is false.
      ##
      # header: false
    
      ## - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
      ## Enable / disable jinja rendering. Default is true. If false, disable Jinja
      ## rendering of the args. Default true.
      ##
      # jinja: true
    
      ## - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
      ## As for csv.writer. Default "
      ##
      # quotechar: '"'
    
      ## - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
      ## As for csv.writer QUOTE_* parameters (without the QUOTE_ prefix). Default
      ## minimal (i.e. QUOTE_MINIMAL).
      ##
      # quoting: "minimal"
    
      ## - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
      ## Suppress splitting of payload files into individual SQL statements.
      ## Default: false (i.e. allow splitting).
      ##
      # raw: false
    
      ## - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
      ## Timeout for each job component script. Default is 10 minutes. Values are in
      ## the form nnX where nn is a number and X is s (seconds), m (minutes) or
      ## h (hours).
      ##
      # timeout: "10m"
    
      ## - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
      ## If true, auto-commit is disabled and the sequence of SQLs is run within a
      ## transaction. If false, auto-commit is enabled. Default false.
      ##
      # transaction: false
    
      ## - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
      ## A map of variables injected when the SQL is Jinja rendered.
      ##
      # vars:
      #   var1: "value1"
      #   var2: "value2"
    ```

## Connection Samples
??? "aws"

    ```yaml
    ## #############################################################################
    ## Mandatory fields
    ##
    conn_id: "???"
    enabled: true
    
    description: "..."
    owner: "<{ owner }>"
    
    ## - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
    ## X-* / x-* vars are ignored by lava but may be useful for other purposes.
    ##
    # X-whatever: "Some value"
    
    type: aws
    
    ## #############################################################################
    ## Connector type specific fields
    
    ## -----------------------------------------------------------------------------
    ## Mandatory fields
    
    # One of `access_keys` or `role_arn` must be specified.
    
    ## - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
    ## The name of an encrypted SSM parameter containing the access keys.
    ## This must be a secure string encrypted using the lava-<REALM>-sys KMS key.
    access_keys: "/lava/<{ realm }>/???"
    
    ## - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
    ## The ARN of a role to assume. The example shows how to construct an ARN in the
    ## same account. Otherwise, a full IAM role ARN is required. Cross account roles
    ## can be used.
    role_arn: "<{ lava.aws.arn('iam-role', 'some-role') }>"
    
    ## -----------------------------------------------------------------------------
    ## Optional fields
    
    ## - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
    ## Name of an SSM parameter containing a unique identifier that may be required
    ## when assuming a (typically cross-account) role.
    external_id: "/lava/<{ realm }>/???"
    
    ## - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
    ## The duration of the role session.
    # duration: 1h
    
    ## - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
    ## IAM managed policies to use as managed session policies.
    # policy_arns:
    #   - policy_arn1
    #   - policy_arn2
    
    ## - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
    ## An IAM policy to use as an inline session policy. This should be expressed as
    ## a full policy object. Lava will manage conversion to JSON
    # policy:
    #  Version: '2012-10-17'
    #  Statement:
    #    - Sid: Stmt1
    #      Effect: Allow
    #      Action: 's3:ListAllMyBuckets'
    #      Resource: '*'
    
    ## - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
    ## A dictionary of tags to apply to the assumed role session.
    # tags:
    #  a: tagA
    #  b: tagB
    
    ## - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
    ## The AWS region name. If not specified, the current region is assumed.
    ##
    # region: "ap-southeast-2"
    ```

??? "docker"

    ```yaml
    ## #############################################################################
    ## Mandatory fields
    ##
    conn_id: "???"
    enabled: true
    
    description: "..."
    owner: "<{ owner }>"
    
    ## - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
    ## X-* / x-* vars are ignored by lava but may be useful for other purposes.
    ##
    # X-whatever: "Some value"
    
    type: docker
    
    ## #############################################################################
    ## Connector type specific fields
    
    ## -----------------------------------------------------------------------------
    ## Mandatory fields
    
    ## -----------------------------------------------------------------------------
    ## Optional fields
    
    ## - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
    ## Email address for registry login
    ##
    # email: "John.Bigbooté@eigth.dimension.com"
    
    ## - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
    ## User name for authenticating to the registry. Required for private docker
    ## repositories. Ignored for ECR registries.
    # user: "..."
    
    ## - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
    ## Name of the SSM parameter containing the password for authenticating to the
    ## registry. Required for private docker repositories. Ignored for ECR
    ## registries. For a given realm, the SSM parameter name must be of the form
    ## /lava/<REALM>/... and the value must be a secure string encrypted using the
    ## lava-<REALM>-sys KMS key
    ##
    # password: "/lava/<{ realm }>/..."
    
    ## - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
    ## Either the URL for a standard registry or ecr[:account-id]. In the latter
    ## case, lava will connect to the AWS ECR registry in the specified AWS account
    ## or the current account if no account-id is specified. If no registry is
    ## specified, the default public docker registry is used
    ##
    # registry: "aws"
    
    ## - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
    ## URL for the docker server. If not specified, then the normal docker
    ## environment variables are used. Generally, this means using the local docker
    ## daemon accessed via the UNIX socket.
    ##
    # server: "..."
    
    ## - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
    ## Timeout on docker API calls in seconds
    ##
    # timeout: 10
    
    ## - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
    ## Use TLS when connecting to the docker server. Default True.
    ##
    # tls: true
    ```

??? "email"

    ```yaml
    ## #############################################################################
    ## Mandatory fields
    ##
    conn_id: "???"
    enabled: true
    
    description: "..."
    owner: "<{ owner }>"
    
    ## - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
    ## X-* / x-* vars are ignored by lava but may be useful for other purposes.
    ##
    # X-whatever: "Some value"
    
    type: ses
    
    ## #############################################################################
    ## Connector type specific fields
    
    ## -----------------------------------------------------------------------------
    ## Mandatory fields
    
    ## -----------------------------------------------------------------------------
    ## Optional fields
    
    ## - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
    ## The email handler subtype. Default is ses.
    # subtype: ses
    
    ## - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
    ## The email address that is sending the email. If not specified, a value must
    ## specified at the realm level.
    ##
    # from: "y2@colossal.cave"
    
    ## - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
    ## Reply-to address(es). Can be string or list of strings.
    ##
    # reply_to: "bedquilt@colossal.cave"
    
    ## -----------------------------------------------------------------------------
    ## ses subtype specific fields
    
    ## - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
    ## The AWS region name for SES. If not specified, us-east-1 is used.
    ##
    # region: "us-east-1"
    ```

??? "generic"

    ```yaml
    ## #############################################################################
    ## Mandatory fields
    ##
    conn_id: "???"
    enabled: true
    
    description: "..."
    owner: "<{ owner }>"
    
    ## - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
    ## X-* / x-* vars are ignored by lava but may be useful for other purposes.
    ##
    # X-whatever: "Some value"
    
    type: generic
    
    ## #############################################################################
    ## Connector type specific fields
    
    ## -----------------------------------------------------------------------------
    ## Mandatory fields
    
    attributes:
      attr1: Sample value
      attr2:
        type: ssm
        parameter: ssm-parameter-name
    
    ## -----------------------------------------------------------------------------
    ## Optional fields
    ```

??? "git"

    ```yaml
    ## #############################################################################
    ## Mandatory fields
    ##
    conn_id: "???"
    enabled: true
    
    description: "..."
    owner: "<{ owner }>"
    
    ## - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
    ## X-* / x-* vars are ignored by lava but may be useful for other purposes.
    ##
    # X-whatever: "Some value"
    
    type: git
    
    ## #############################################################################
    ## Connector type specific fields
    
    ## -----------------------------------------------------------------------------
    ## Mandatory fields
    
    ## - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
    ## The name of an encrypted SSM parameter containing the SSH private key.
    ## This must be a secure string encrypted using the lava-<REALM>-sys KMS key.
    ##
    ssh_key: "/lava/<{ realm }>/???"
    
    ## -----------------------------------------------------------------------------
    ## Optional fields
    ```

??? "mariadb-rds"

    ```yaml
    ## #############################################################################
    ## Mandatory fields
    ##
    conn_id: "???"
    enabled: true
    
    description: "..."
    owner: "<{ owner }>"
    
    ## - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
    ## X-* / x-* vars are ignored by lava but may be useful for other purposes.
    ##
    # X-whatever: "Some value"
    
    type: mysql
    
    ## #############################################################################
    ## Connector type specific fields
    
    ## -----------------------------------------------------------------------------
    ## Conditional fields - Required but may come from Secrets Manager
    
    ## - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
    ## The name of the database (schema) within the database server.
    ##
    database: "???"
    
    ## - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
    ## The database host DNS name or IP address.
    ##
    host: "???"
    
    ## - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
    ## The name of an encrypted SSM parameter containing the password.
    ## This must be a secure string encrypted using the lava-<REALM>-sys KMS key.
    ##
    password: "/lava/<{ realm }>/???"
    
    ## - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
    ## Port number.
    ##
    port: ???
    
    ## - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
    ## User name.
    ##
    user: "???"
    
    ## -----------------------------------------------------------------------------
    ## Optional fields
    
    ## - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
    ## Name of a secret in AWS Secrets Manager
    # secret_id: /lava/<{ realm }>/secret-name
    
    ## - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
    ## The subtype specifies the driver to use.
    # subtype: pymysql
    
    ## - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
    ## The name of a file containing the CA certificate for the database server.
    ## Ignored unless ssl is true.
    ##
    # ca_cert: "/usr/local/lib/rds/rds-ca-2019-root.pem"
    
    ## - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
    ## Set to true to enable SSL. Default is false
    ##
    # ssl: false
    ```

??? "mariadb"

    ```yaml
    ## #############################################################################
    ## Mandatory fields
    ##
    conn_id: "???"
    enabled: true
    
    description: "..."
    owner: "<{ owner }>"
    
    ## - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
    ## X-* / x-* vars are ignored by lava but may be useful for other purposes.
    ##
    # X-whatever: "Some value"
    
    type: mysql
    
    ## #############################################################################
    ## Connector type specific fields
    
    ## -----------------------------------------------------------------------------
    ## Conditional fields - Required but may come from Secrets Manager
    
    ## - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
    ## The name of the database (schema) within the database server.
    ##
    database: "???"
    
    ## - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
    ## The database host DNS name or IP address.
    ##
    host: "???"
    
    ## - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
    ## The name of an encrypted SSM parameter containing the password.
    ## This must be a secure string encrypted using the lava-<REALM>-sys KMS key.
    ##
    password: "/lava/<{ realm }>/???"
    
    ## - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
    ## Port number.
    ##
    port: ???
    
    ## - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
    ## User name.
    ##
    user: "???"
    
    ## -----------------------------------------------------------------------------
    ## Optional fields
    
    ## - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
    ## Name of a secret in AWS Secrets Manager
    # secret_id: /lava/<{ realm }>/secret-name
    
    ## - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
    ## The subtype specifies the driver to use.
    # subtype: pymysql
    
    ## - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
    ## The name of a file containing the CA certificate for the database server.
    ## Ignored unless ssl is true.
    ##
    # ca_cert: "/usr/local/lib/rds/rds-ca-2019-root.pem"
    
    ## - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
    ## Set to true to enable SSL. Default is false
    ##
    # ssl: false
    ```

??? "mysql-aurora"

    ```yaml
    ## #############################################################################
    ## Mandatory fields
    ##
    conn_id: "???"
    enabled: true
    
    description: "..."
    owner: "<{ owner }>"
    
    ## - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
    ## X-* / x-* vars are ignored by lava but may be useful for other purposes.
    ##
    # X-whatever: "Some value"
    
    type: mysql
    
    ## #############################################################################
    ## Connector type specific fields
    
    ## -----------------------------------------------------------------------------
    ## Conditional fields - Required but may come from Secrets Manager
    
    ## - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
    ## The name of the database (schema) within the database server.
    ##
    database: "???"
    
    ## - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
    ## The database host DNS name or IP address.
    ##
    host: "???"
    
    ## - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
    ## The name of an encrypted SSM parameter containing the password.
    ## This must be a secure string encrypted using the lava-<REALM>-sys KMS key.
    ##
    password: "/lava/<{ realm }>/???"
    
    ## - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
    ## Port number.
    ##
    port: ???
    
    ## - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
    ## User name.
    ##
    user: "???"
    
    ## -----------------------------------------------------------------------------
    ## Optional fields
    
    ## - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
    ## Name of a secret in AWS Secrets Manager
    # secret_id: /lava/<{ realm }>/secret-name
    
    ## - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
    ## The subtype specifies the driver to use.
    # subtype: pymysql
    
    ## - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
    ## The name of a file containing the CA certificate for the database server.
    ## Ignored unless ssl is true.
    ##
    # ca_cert: "/usr/local/lib/rds/rds-ca-2019-root.pem"
    
    ## - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
    ## Set to true to enable SSL. Default is false
    ##
    # ssl: false
    ```

??? "mysql-rds"

    ```yaml
    ## #############################################################################
    ## Mandatory fields
    ##
    conn_id: "???"
    enabled: true
    
    description: "..."
    owner: "<{ owner }>"
    
    ## - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
    ## X-* / x-* vars are ignored by lava but may be useful for other purposes.
    ##
    # X-whatever: "Some value"
    
    type: mysql
    
    ## #############################################################################
    ## Connector type specific fields
    
    ## -----------------------------------------------------------------------------
    ## Conditional fields - Required but may come from Secrets Manager
    
    ## - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
    ## The name of the database (schema) within the database server.
    ##
    database: "???"
    
    ## - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
    ## The database host DNS name or IP address.
    ##
    host: "???"
    
    ## - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
    ## The name of an encrypted SSM parameter containing the password.
    ## This must be a secure string encrypted using the lava-<REALM>-sys KMS key.
    ##
    password: "/lava/<{ realm }>/???"
    
    ## - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
    ## Port number.
    ##
    port: ???
    
    ## - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
    ## User name.
    ##
    user: "???"
    
    ## -----------------------------------------------------------------------------
    ## Optional fields
    
    ## - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
    ## Name of a secret in AWS Secrets Manager
    # secret_id: /lava/<{ realm }>/secret-name
    
    ## - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
    ## The subtype specifies the driver to use.
    # subtype: pymysql
    
    ## - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
    ## The name of a file containing the CA certificate for the database server.
    ## Ignored unless ssl is true.
    ##
    # ca_cert: "/usr/local/lib/rds/rds-ca-2019-root.pem"
    
    ## - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
    ## Set to true to enable SSL. Default is false
    ##
    # ssl: false
    ```

??? "mysql"

    ```yaml
    ## #############################################################################
    ## Mandatory fields
    ##
    conn_id: "???"
    enabled: true
    
    description: "..."
    owner: "<{ owner }>"
    
    ## - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
    ## X-* / x-* vars are ignored by lava but may be useful for other purposes.
    ##
    # X-whatever: "Some value"
    
    type: mysql
    
    ## #############################################################################
    ## Connector type specific fields
    
    ## -----------------------------------------------------------------------------
    ## Conditional fields - Required but may come from Secrets Manager
    
    ## - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
    ## The name of the database (schema) within the database server.
    ##
    database: "???"
    
    ## - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
    ## The database host DNS name or IP address.
    ##
    host: "???"
    
    ## - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
    ## The name of an encrypted SSM parameter containing the password.
    ## This must be a secure string encrypted using the lava-<REALM>-sys KMS key.
    ##
    password: "/lava/<{ realm }>/???"
    
    ## - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
    ## Port number.
    ##
    port: ???
    
    ## - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
    ## User name.
    ##
    user: "???"
    
    ## -----------------------------------------------------------------------------
    ## Optional fields
    
    ## - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
    ## Name of a secret in AWS Secrets Manager
    # secret_id: /lava/<{ realm }>/secret-name
    
    ## - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
    ## The subtype specifies the driver to use.
    # subtype: pymysql
    
    ## - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
    ## The name of a file containing the CA certificate for the database server.
    ## Ignored unless ssl is true.
    ##
    # ca_cert: "/usr/local/lib/rds/rds-ca-2019-root.pem"
    
    ## - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
    ## Set to true to enable SSL. Default is false
    ##
    # ssl: false
    ```

??? "oracle-rds"

    ```yaml
    ## #############################################################################
    ## Mandatory fields
    ##
    conn_id: "???"
    enabled: true
    
    description: "..."
    owner: "<{ owner }>"
    
    ## - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
    ## X-* / x-* vars are ignored by lava but may be useful for other purposes.
    ##
    # X-whatever: "Some value"
    
    type: oracle
    
    ## #############################################################################
    ## Connector type specific fields
    
    ## -----------------------------------------------------------------------------
    ## Conditional fields - Required but may come from Secrets Manager
    
    
    ## - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
    ## The database host DNS name or IP address.
    ##
    host: "???"
    
    ## - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
    ## The name of an encrypted SSM parameter containing the password.
    ## This must be a secure string encrypted using the lava-<REALM>-sys KMS key.
    ##
    password: "/lava/<{ realm }>/???"
    
    ## - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
    ## Port number.
    ##
    port: ???
    
    ## - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
    ## User name.
    ##
    user: "???"
    
    ## -----------------------------------------------------------------------------
    ## Optional fields
    
    ## - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
    ## Name of a secret in AWS Secrets Manager
    # secret_id: /lava/<{ realm }>/secret-name
    
    ## - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
    ## Oracle version for compatibility in the form x.y[.z].
    ##
    # edition: "x.y.z"
    
    ## - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
    ## The subtype specifies the driver to use.
    # subtype: cx_oracle
    
    ## - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
    ## The Oracle database service name. Generally exactly one of service_name or
    ## sid must be specified.
    ##
    # service_name: "???"
    
    ## - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
    ## The Oracle System Identifier of the database. Generally exactly one of
    ## service_name or sid must be specified.
    ##
    # sid: "???"
    ```

??? "oracle"

    ```yaml
    ## #############################################################################
    ## Mandatory fields
    ##
    conn_id: "???"
    enabled: true
    
    description: "..."
    owner: "<{ owner }>"
    
    ## - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
    ## X-* / x-* vars are ignored by lava but may be useful for other purposes.
    ##
    # X-whatever: "Some value"
    
    type: oracle
    
    ## #############################################################################
    ## Connector type specific fields
    
    ## -----------------------------------------------------------------------------
    ## Conditional fields - Required but may come from Secrets Manager
    
    
    ## - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
    ## The database host DNS name or IP address.
    ##
    host: "???"
    
    ## - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
    ## The name of an encrypted SSM parameter containing the password.
    ## This must be a secure string encrypted using the lava-<REALM>-sys KMS key.
    ##
    password: "/lava/<{ realm }>/???"
    
    ## - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
    ## Port number.
    ##
    port: ???
    
    ## - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
    ## User name.
    ##
    user: "???"
    
    ## -----------------------------------------------------------------------------
    ## Optional fields
    
    ## - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
    ## Name of a secret in AWS Secrets Manager
    # secret_id: /lava/<{ realm }>/secret-name
    
    ## - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
    ## Oracle version for compatibility in the form x.y[.z].
    ##
    # edition: "x.y.z"
    
    ## - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
    ## The subtype specifies the driver to use.
    # subtype: cx_oracle
    
    ## - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
    ## The Oracle database service name. Generally exactly one of service_name or
    ## sid must be specified.
    ##
    # service_name: "???"
    
    ## - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
    ## The Oracle System Identifier of the database. Generally exactly one of
    ## service_name or sid must be specified.
    ##
    # sid: "???"
    ```

??? "postgres-aurora"

    ```yaml
    ## #############################################################################
    ## Mandatory fields
    ##
    conn_id: "???"
    enabled: true
    
    description: "..."
    owner: "<{ owner }>"
    
    ## - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
    ## X-* / x-* vars are ignored by lava but may be useful for other purposes.
    ##
    # X-whatever: "Some value"
    
    type: postgres
    
    ## #############################################################################
    ## Connector type specific fields
    
    ## -----------------------------------------------------------------------------
    ## Conditional fields - Required but may come from Secrets Manager
    
    ## - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
    ## The name of the database (schema) within the database server.
    ##
    database: "???"
    
    ## - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
    ## The database host DNS name or IP address.
    ##
    host: "???"
    
    ## - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
    ## The name of an encrypted SSM parameter containing the password.
    ## This must be a secure string encrypted using the lava-<REALM>-sys KMS key.
    ##
    password: "/lava/<{ realm }>/???"
    
    ## - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
    ## Port number.
    ##
    port: ???
    
    ## - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
    ## User name.
    ##
    user: "???"
    
    ## -----------------------------------------------------------------------------
    ## Optional fields
    
    ## - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
    ## Name of a secret in AWS Secrets Manager
    # secret_id: /lava/<{ realm }>/secret-name
    
    ## - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
    ## The subtype specifies the driver to use.
    # subtype: pg8000
    
    ## - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
    ## Set to true to enable SSL. Default is false
    ##
    # ssl: false
    ```

??? "postgres-rds"

    ```yaml
    ## #############################################################################
    ## Mandatory fields
    ##
    conn_id: "???"
    enabled: true
    
    description: "..."
    owner: "<{ owner }>"
    
    ## - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
    ## X-* / x-* vars are ignored by lava but may be useful for other purposes.
    ##
    # X-whatever: "Some value"
    
    type: postgres
    
    ## #############################################################################
    ## Connector type specific fields
    
    ## -----------------------------------------------------------------------------
    ## Conditional fields - Required but may come from Secrets Manager
    
    ## - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
    ## The name of the database (schema) within the database server.
    ##
    database: "???"
    
    ## - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
    ## The database host DNS name or IP address.
    ##
    host: "???"
    
    ## - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
    ## The name of an encrypted SSM parameter containing the password.
    ## This must be a secure string encrypted using the lava-<REALM>-sys KMS key.
    ##
    password: "/lava/<{ realm }>/???"
    
    ## - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
    ## Port number.
    ##
    port: ???
    
    ## - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
    ## User name.
    ##
    user: "???"
    
    ## -----------------------------------------------------------------------------
    ## Optional fields
    
    ## - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
    ## Name of a secret in AWS Secrets Manager
    # secret_id: /lava/<{ realm }>/secret-name
    
    ## - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
    ## The subtype specifies the driver to use.
    # subtype: pg8000
    
    ## - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
    ## Set to true to enable SSL. Default is false
    ##
    # ssl: false
    ```

??? "postgres"

    ```yaml
    ## #############################################################################
    ## Mandatory fields
    ##
    conn_id: "???"
    enabled: true
    
    description: "..."
    owner: "<{ owner }>"
    
    ## - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
    ## X-* / x-* vars are ignored by lava but may be useful for other purposes.
    ##
    # X-whatever: "Some value"
    
    type: postgres
    
    ## #############################################################################
    ## Connector type specific fields
    
    ## -----------------------------------------------------------------------------
    ## Conditional fields - Required but may come from Secrets Manager
    
    ## - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
    ## The name of the database (schema) within the database server.
    ##
    database: "???"
    
    ## - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
    ## The database host DNS name or IP address.
    ##
    host: "???"
    
    ## - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
    ## The name of an encrypted SSM parameter containing the password.
    ## This must be a secure string encrypted using the lava-<REALM>-sys KMS key.
    ##
    password: "/lava/<{ realm }>/???"
    
    ## - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
    ## Port number.
    ##
    port: ???
    
    ## - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
    ## User name.
    ##
    user: "???"
    
    ## -----------------------------------------------------------------------------
    ## Optional fields
    
    ## - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
    ## Name of a secret in AWS Secrets Manager
    # secret_id: /lava/<{ realm }>/secret-name
    
    ## - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
    ## The subtype specifies the driver to use.
    # subtype: pg8000
    
    ## - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
    ## Set to true to enable SSL. Default is false
    ##
    # ssl: false
    ```

??? "psql"

    ```yaml
    ## #############################################################################
    ## Mandatory fields
    ##
    conn_id: "???"
    enabled: true
    
    description: "..."
    owner: "<{ owner }>"
    
    ## - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
    ## X-* / x-* vars are ignored by lava but may be useful for other purposes.
    ##
    # X-whatever: "Some value"
    
    type: postgres
    
    ## #############################################################################
    ## Connector type specific fields
    
    ## -----------------------------------------------------------------------------
    ## Conditional fields - Required but may come from Secrets Manager
    
    ## - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
    ## The name of the database (schema) within the database server.
    ##
    database: "???"
    
    ## - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
    ## The database host DNS name or IP address.
    ##
    host: "???"
    
    ## - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
    ## The name of an encrypted SSM parameter containing the password.
    ## This must be a secure string encrypted using the lava-<REALM>-sys KMS key.
    ##
    password: "/lava/<{ realm }>/???"
    
    ## - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
    ## Port number.
    ##
    port: ???
    
    ## - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
    ## User name.
    ##
    user: "???"
    
    ## -----------------------------------------------------------------------------
    ## Optional fields
    
    ## - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
    ## Name of a secret in AWS Secrets Manager
    # secret_id: /lava/<{ realm }>/secret-name
    
    ## - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
    ## The subtype specifies the driver to use.
    # subtype: pg8000
    
    ## - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
    ## Set to true to enable SSL. Default is false
    ##
    # ssl: false
    ```

??? "redshift-serverless"

    ```yaml
    ## #############################################################################
    ## Mandatory fields
    ##
    conn_id: "???"
    enabled: true
    
    description: "..."
    owner: "<{ owner }>"
    
    ## - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
    ## X-* / x-* vars are ignored by lava but may be useful for other purposes.
    ##
    # X-whatever: "Some value"
    
    type: redshift-serverless
    
    ## #############################################################################
    ## Connector type specific fields
    
    ## -----------------------------------------------------------------------------
    ## Conditional fields - Required but may come from Secrets Manager
    
    ## - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
    ## The name of the database within the Redshift Serverless namespace.
    ##
    database: "???"
    
    ## - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
    ## The Redshift serverless workgroup endpoint address.
    ##
    host: "???"
    
    ## - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
    ## The name of an encrypted SSM parameter containing the password.
    ## This must be a secure string encrypted using the lava-<REALM>-sys KMS key.
    ## If not provided, IAM authentication to Redshift Serverless is attempted.
    ##
    password: "/lava/<{ realm }>/???"
    
    ## - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
    ## Port number.
    ##
    port: ???
    
    ## - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
    ## User name. This is required except when using secrets managaer or IAM based
    ## authentication.
    ##
    user: "???"
    
    ## -----------------------------------------------------------------------------
    ## Optional fields
    
    ## - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
    ## Name of an SSM parameter containing an external ID to use when assuming the
    ## IAM role specified by role_arn.
    ##
    # external_id: ...
    
    ## - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
    ## Name of a secret in AWS Secrets Manager
    # secret_id: /lava/<{ realm }>/secret-name
    
    ## - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
    ## The password duration when generating temporary IAM user credientials.
    ##
    # password_duration: "15m"
    
    ## - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
    ## don't fold database object names to lower case when quoting for db_from_s3 jobs
    ##
    # preserve_case: False
    
    ## - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
    ## ARN of IAM role to be assumed when generating temporary IAM user credentials.
    ##
    # role_arn: ...
    
    ## - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
    ## Set to true to enable SSL. Default is false.
    ##
    # ssl: false
    
    ## - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
    ## The subtype specifies the driver to use.
    # subtype: pg8000
    
    ## - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
    ## Name of the workgroup associated with the database. Used when generating
    ## temporary IAM user credentials. Defaults to the first component of the host.
    ##
    # workgroup: ...
    ```

??? "redshift"

    ```yaml
    ## #############################################################################
    ## Mandatory fields
    ##
    conn_id: "???"
    enabled: true
    
    description: "..."
    owner: "<{ owner }>"
    
    ## - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
    ## X-* / x-* vars are ignored by lava but may be useful for other purposes.
    ##
    # X-whatever: "Some value"
    
    type: redshift
    
    ## #############################################################################
    ## Connector type specific fields
    
    ## -----------------------------------------------------------------------------
    ## Conditional fields - Required but may come from Secrets Manager
    
    ## - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
    ## The name of the database within the database server.
    ##
    database: "???"
    
    ## - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
    ## The database host DNS name or IP address.
    ##
    host: "???"
    
    ## - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
    ## The name of an encrypted SSM parameter containing the password.
    ## This must be a secure string encrypted using the lava-<REALM>-sys KMS key.
    ## If not provided, IAM authentication to Redshift is attempted.
    ##
    password: "/lava/<{ realm }>/???"
    
    ## - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
    ## Port number.
    ##
    port: ???
    
    ## - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
    ## User name.
    ##
    user: "???"
    
    ## -----------------------------------------------------------------------------
    ## Optional fields
    
    ## - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
    ## The Redshift cluster identifier. Default is first part of host name.
    ##
    # cluster_id: my_cluster
    
    ## - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
    ## Name of a secret in AWS Secrets Manager
    # secret_id: /lava/<{ realm }>/secret-name
    
    ## - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
    ## The password duration when generating temporary IAM user credientials.
    ##
    # password_duration: "15m"
    
    ### - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
    ### don't fold database object names to lower case when quoting for db_from_s3 jobs
    ###
    ## preserve_case: False
    
    ## - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
    ## Set to true to enable SSL. Default is false
    ##
    # ssl: false
    
    ## - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
    ## The subtype specifies the driver to use.
    # subtype: pg8000
    ```

??? "scp"

    ```yaml
    ## #############################################################################
    ## Mandatory fields
    ##
    conn_id: "???"
    enabled: true
    
    description: "..."
    owner: "<{ owner }>"
    
    ## - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
    ## X-* / x-* vars are ignored by lava but may be useful for other purposes.
    ##
    # X-whatever: "Some value"
    
    type: scp
    
    ## #############################################################################
    ## Connector type specific fields
    
    ## -----------------------------------------------------------------------------
    ## Mandatory fields
    
    ## - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
    ## The name of an encrypted SSM parameter containing the SSH private key.
    ## This must be a secure string encrypted using the lava-<REALM>-sys KMS key.
    ##
    ssh_key: "/lava/<{ realm }>/???"
    
    ## -----------------------------------------------------------------------------
    ## Optional fields
    ```

??? "ses"

    ```yaml
    ## #############################################################################
    ## Mandatory fields
    ##
    conn_id: "???"
    enabled: true
    
    description: "..."
    owner: "<{ owner }>"
    
    ## - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
    ## X-* / x-* vars are ignored by lava but may be useful for other purposes.
    ##
    # X-whatever: "Some value"
    
    ## -----------------------------------------------------------------------------
    ## This is a legacy connector. Use email instead.
    ## -----------------------------------------------------------------------------
    
    type: ses
    
    ## #############################################################################
    ## Connector type specific fields
    
    ## -----------------------------------------------------------------------------
    ## Mandatory fields
    
    ## -----------------------------------------------------------------------------
    ## Optional fields
    
    ## - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
    ## The email address that is sending the email. If not specified, a value must
    ## specified at the realm level.
    ##
    # from: "y2@colossal.cave"
    
    ## - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
    ## Reply-to address(es). Can be string or list of strings.
    ##
    # reply_to: "bedquilt@colossal.cave"
    
    ## - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
    ## The email address that bounces and complaints will be forwarded to when
    ## feedback forwarding is enabled
    ##
    # return_path: "plugh@colossal.cave"
    
    ## - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
    ## The AWS region name for SES. If not specified, us-east-1 is used.
    ##
    # region: "us-east-1"
    ```

??? "sftp"

    ```yaml
    ## #############################################################################
    ## Mandatory fields
    ##
    conn_id: "???"
    enabled: true
    
    description: "..."
    owner: "<{ owner }>"
    
    ## - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
    ## X-* / x-* vars are ignored by lava but may be useful for other purposes.
    ##
    # X-whatever: "Some value"
    
    type: sftp
    
    ## #############################################################################
    ## Connector type specific fields
    
    ## -----------------------------------------------------------------------------
    ## Mandatory fields
    
    ## - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
    ## The name of an encrypted SSM parameter containing the SSH private key.
    ## This must be a secure string encrypted using the lava-<REALM>-sys KMS key.
    ##
    ssh_key: "/lava/<{ realm }>/???"
    
    ## -----------------------------------------------------------------------------
    ## Optional fields
    ```

??? "sharepoint"

    ```yaml
    ## #############################################################################
    ## Mandatory fields
    ##
    conn_id: "???"
    enabled: true
    
    description: "..."
    owner: "<{ owner }>"
    
    ## - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
    ## X-* / x-* vars are ignored by lava but may be useful for other purposes.
    ##
    # X-whatever: "Some value"
    
    type: sharepoint
    
    ## #############################################################################
    ## Connector type specific fields
    
    ## -----------------------------------------------------------------------------
    ## Mandatory fields
    
    ## - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
    ## The Application ID that the SharePoint registration portal assigned your app.
    ## This resembles a UUID.
    ##
    client_name: "???"
    
    ## - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
    ## SSM parameter containing the client secret.
    ## This must be a secure string encrypted using the lava-<REALM>-sys KMS key.
    ##
    client_secret: "/lava/<{ realm }>/???"
    
    ## - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
    ## The organisation’s SharePoint base URL. e.g. acme.sharepoint.com.
    ##
    org_base_url: "???"
    
    ## - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
    ## SSM parameter containing password for authenticating to SharePoint.
    ## This must be a secure string encrypted using the lava-<REALM>-sys KMS key.
    ##
    password: "/lava/<{ realm }>/???"
    
    ## - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
    ## SharePoint site name.
    ##
    site_name: "???"
    
    ## - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
    ## Azure AD registered domain ID.
    tenant: "???"
    
    ## -----------------------------------------------------------------------------
    ## Optional fields
    
    ## - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
    ## User name for authenticating to SharePoint.
    ##
    # user: "???"
    ```

??? "smb"

    ```yaml
    ## #############################################################################
    ## Mandatory fields
    ##
    conn_id: "???"
    enabled: true
    
    description: "..."
    owner: "<{ owner }>"
    
    ## - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
    ## X-* / x-* vars are ignored by lava but may be useful for other purposes.
    ##
    # X-whatever: "Some value"
    
    type: smb
    
    ## #############################################################################
    ## Connector type specific fields
    
    ## -----------------------------------------------------------------------------
    ## Mandatory fields
    
    ## - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
    ## The database host DNS name or IP address.
    ##
    host: "???"
    
    ## - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
    ## NetBIOS machine name of the remote server.
    ##
    remote_name: "???"
    
    ## - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
    ## SSM parameter containing password for authenticating to the SMB server.
    ## This must be a secure string encrypted using the lava-<REALM>-sys KMS key.
    ##
    password: "/lava/<{ realm }>/???"
    
    ## - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
    ## User name for authenticating to the SMB server.
    ##
    user: "???"
    
    ## -----------------------------------------------------------------------------
    ## Optional fields
    
    ## - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
    ## The connection subtype. Choose between 'pysmb' and 'smbprotocol'. smbprotocol
    ## supports encryption and access via DFS. Defaults to 'pysmb'.
    ##
    # subtype: "smbprotocol"
    
    ## - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
    ## The network domain. Defaults to an empty string.
    ##
    ## In the 'smbprotocol' job subtype, domain can refer to a DFS domain.
    ## Connecting via DFS is not supported in the 'pysmb' job subtype.
    ##
    # domain: ""
    
    ## - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
    ## A custom port to use. Defaults to 445 if is_direct_tcp is True else 139.
    ##
    # port: 445
    
    ## - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
    ## If false, request and transfer files without encryption. If true use encryption.
    ##
    ## Default is True when using the 'smbprotocol' job subtype.
    ## The 'pysmb' job subtype doesn't support encryption.
    ##
    # encrypt: false
    
    ## - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
    ## If false, use NetBIOS over TCP/IP. If true use SMB over TCP/IP. Default false.
    ##
    # is_direct_tcp: false
    
    ## - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
    ## Local NetBIOS machine name that will identify the origin of connections. If
    ## not specified, defaults to the first 15 characters of lava-<REALM>
    ##
    # my_name: "<{ ('lava-' + realm)[:15] }>"
    
    ## - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
    ## Indicates whether pysmb should be NTLMv1 or NTLMv2 authentication algorithm
    ## for authentication. Default is true.
    ##
    # use_ntlm_v2: true
    ```

??? "ssh"

    ```yaml
    ## #############################################################################
    ## Mandatory fields
    ##
    conn_id: "???"
    enabled: true
    
    description: "..."
    owner: "<{ owner }>"
    
    ## - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
    ## X-* / x-* vars are ignored by lava but may be useful for other purposes.
    ##
    # X-whatever: "Some value"
    
    type: ssh
    
    ## #############################################################################
    ## Connector type specific fields
    
    ## -----------------------------------------------------------------------------
    ## Mandatory fields
    
    ## - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
    ## The name of an encrypted SSM parameter containing the SSH private key.
    ## This must be a secure string encrypted using the lava-<REALM>-sys KMS key.
    ##
    ssh_key: "/lava/<{ realm }>/???"
    
    ## -----------------------------------------------------------------------------
    ## Optional fields
    ```

## Rule Samples
??? "common"

    ```yaml
    ## #############################################################################
    ## Mandatory fields
    ##
    rule_id: "<{ prefix.rule }>.demo"
    enabled: true
    owner: "<{ owner }>"
    description: "Rule description"
    
    ## #############################################################################
    ## Optional fields
    ##
    
    ## - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
    ## Event bus name. This should almost always be left out to use the default bus.
    ##
    # event_bus_name: default
    
    ## - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
    ## Event pattern. This will almost always be required. The example shown is an
    ## S3 object creation event.
    ##
    # event_pattern:
    #   detail:
    #     bucket:
    #       name:
    #         - my-bucket
    #     object:
    #       key:
    #         - prefix: a/prefix/in/the/bucket/
    #   detail-type:
    #     - Object Created
    #   source:
    #     - aws.s3
    
    ## - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
    ## Schedule expression (cron or rate based). Usually only one of event_pattern
    ## and schedule_expression are required.
    ##
    # schedule_expression: "rate(1 day)"
    
    ## - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
    ## The ARN of the IAM role associated with the rule. Not needed for basic use
    ## cases such as s3trigger and logging events to CloudWatch.
    ##
    # role_arn: "<{ lava.aws.arn('iam-role', 'my-role-name') }>"
    
    ## - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
    ## Event targets. This is required if you want the rule to do anything. The
    ## example shown is for using s3trigger to dispatch a job on an S3 event.
    ##
    # targets:
    #   # Construct the ARN for the realm s3trigger lambda
    #   - <{ lava.aws.arn('lambda-function', 'lava-' + realm + '-s3trigger') }>
    #   # Let's log messages in CloudWatch logs
    #   - <{ lava.aws.arn('log-group', '/aws/events/lava') }>
    
    ## - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
    ## Tags for the rule.
    ##
    # tags:
    #   key1: val1
    #   key2: val2
    ```

## S3trigger Samples
??? "common"

    ```yaml
    ## #############################################################################
    ## Mandatory fields
    ##
    trigger_id: "<{ prefix.s3trigger }>/???"
    enabled: true
    job_id: "<{ prefix.job }>/???"
    bucket: "???"
    prefix: "???"
    
    ## #############################################################################
    ## Optional fields
    ##
    description: "..."
    owner: "<{ owner }>"
    
    ## - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
    ## Dispatch message sending delay in the form nnX where nn is a number and X
    ## is s (seconds) or m (minutes). The maximum allowed value is 15 minutes.
    ##
    # delay: "5m"
    
    ## - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
    ## Enable / disable jinja rendering. Default is true. If false, disable Jinja
    ## rendering of the parameters and globals.
    ##
    # jinja: true
    
    ## - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
    ## Globals for the dispatched job
    ##
    # globals:
    #   global1: val1
    #   global2: val2
    
    ## - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
    ## Parameters for the dispatched job
    ##
    # parameters:
    #   param1: val1
    #   param2: val2
    
    
    ## - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
    ## X-* / x-* vars are ignored by lava but may be useful for other purposes.
    ##
    # X-whatever: "Some value"
    ```

