
## Instrumentation and Monitoring of Lava { data-toc-label="Instrumentation & Monitoring" }

Lava has the following instrumentation and monitoring facilities:

*   Lava worker and dispatcher [logging](#logging).

*   Logging to AWS CloudWatch logs for the lambda functions.

*   [AWS CloudWatch custom metrics](#cloudwatch-metrics) for
    lava jobs and internal worker behaviour.

*   Predefined [AWS CloudWatch alarms](#cloudwatch-alarms).

### Logging

Both the worker and dispatcher accept a range of options to control logging.

Capabilities include:

*   Generating a heartbeat message at a defined interval (worker only).

*   Setting logging level anywhere between `debug` and `critical`.

*   Logging to stderr, a file or designated syslog facility.

*   Tagging log entries so they can be filtered from other unrelated logs.

*   Logging in text or JSON format.

For more information:

```bash
lava-worker --help
lava-dispatcher --help
```

The standard production configuration for the worker when running on the
[lava AMI](#the-lava-ec2-ami) is:

*   Set the logging level to `info`

*   Generate a heartbeat every 60 seconds. This is also used to trigger
    heartbeat

*   Log in JSON format to the `local0` syslog facility which is directed to the
    file `/var/log/lava` on the worker machine. (The messages are also included
    in the general system log in the file `/var/log/messages`.)

*   The `/var/log/lava` log file is automatically replicated to the CloudWatch
    log group `/var/log/lava/<REALM>`.



A typical message (although on a single line) appears thus:


```json
{
  "event_source": "lava-worker",
  "realm": "dev",
  "worker": "core",
  "host": "my-host",
  "tag": "lava-worker",
  "timestamp": "2023-05-11 15:04:36",
  "level": "INFO",
  "message": "Job cmd/hello-world (2ce3ac8e-0fc2-41f1-b908-998608a0b24b): Complete",
  "thread": "worker-00",
  "pid": 37273,
  "event_type": "job",
  "job_id": "test/cmd/hello-world",
  "run_id": "2ce3ac8e-0fc2-41f1-b908-998608a0b24b"
}
```

The following search predicate would find this record in CloudWatch logs:

```
{ $.realm=dev && $.job=cmd/hello-world && $.run_id=2ce3ac8e-0fc2-41f1-b908-998608a0b24b }
```

The log group can also be queried using CloudWatch Log Insights. The
(approximately) equivalent Insights query is:

```
fields @timestamp, @message, @logStream, @log
| filter realm = "dev" and job_id="cmd/hello-world" and run_id="2ce3ac8e-0fc2-41f1-b908-998608a0b24b"
| sort @timestamp desc
```

As is usual for Lambda functions, the lava lambdas also log directly to
CloudWatch.

### Heartbeats

When used with the worker startup script provided for use in production
deployments, the lava worker emits a heartbeat message to syslog every 60
seconds. These records propagate to the CloudWatch log group `/var/log/messages`.
A log metric filter on this group is used as the basis of a CloudWatch Metric
which underpins an alarm in the event of loss of heartbeat. This is all configured
via the [worker CloudFormation stack](#building-the-cloudformation-templates).

As of v7.1.0 (Pichincha), the heartbeat message also contains additional worker
health information. A typical heartbeat message (although on a single line)
appears thus:

```json
{
  "event_source": "lava-worker",
  "realm": "dev",
  "worker": "core",
  "host": "my-host",
  "tag": "lava-worker",
  "timestamp": "2023-05-11 18:09:23",
  "level": "INFO",
  "message": "heartbeat realm=dev worker=core",
  "thread": "heartbeat",
  "pid": 37273,
  "event_type": "heartbeat",
  "sqs": {
    "messages": 0,
    "notvisible": 0
  },
  "internal": {
    "qlen": 0
  },
  "threads": {
    "event": "OK",
    "worker-00": "OK",
    "worker-01": "OK",
    "heartbeat": "OK",
    "metrics": "OK"
  }
}
```

The various threads perform the following functions:

|Thread|Description|
|-|------|
|event|Send events to the DynamoDB [events table](#the-events-table).|
|heartbeat|Emit heartbeat messages.|
|metrics|Send metric data to CloudWatch.|
|worker-*|Run lava jobs.|

### CloudWatch Metrics

The lava worker can generate CloudWatch custom metrics for individual jobs and
for the worker itself.

#### Job Metrics

Job metrics can be enabled at the realm level or at the individual job level.
The following process is used to determine if metric data will be produced:

1.  If the `cw_metrics` field is set in the
    [job specification](#the-jobs-table), that value is used to
    either enable or disable metric data generation.

2.  Otherwise, the value specified at the
    [worker or realm level](#lava-worker-configuration) via the 
    [CW_METRICS_JOB parameter](#general-configuration-parameters)
    is used.

If enabled, the following job metrics are produced for each job:

|Metric|Dimensions|Description|
|-|-|----|
|JobFailed|Realm, Job|`0` if the job succeeded and `1` if it failed.|
|RunDelay|Realm, Worker|The time in seconds between job dispatch and job start. This should normally be under 10 seconds. Values above this may indicate the worker is overloaded.|
|RunTime|Realm, Job|The runtime in seconds of the job from when it started to the completion of any post-job actions.|

#### Worker Metrics

Worker metrics can be enabled at the 
[worker or realm level](#lava-worker-configuration) via the 
[CW_METRICS_WORKER parameter](#general-configuration-parameters).

If enabled, the following worker metrics are produced:

|Metric|Dimensions|Description|
|-|-|----|
|MaxRss|Realm, Worker, Instance|The maximum resident set size for the main worker process. See [getrusage(2)](http://man7.org/linux/man-pages/man2/getrusage.2.html) for more information.|
|PercentDiskUsed|Realm, Worker, Instance|This is a deprecated name for `PercentTmpDiskUsed`. It will be removed in a future release.|
|PercentDockerDiskUsed|Realm, Worker, Instance|The percentage of disk space used for the docker volume on the worker, if present.|
|PercentMemUsed|Realm, Worker, Instance|The percentage of memory used on the worker measured as the total physical memory minus the memory that can be given instantly to processes without the system going into swap. See [psutil.virtual_memory()](https://psutil.readthedocs.io/en/latest/).|
|PercentSwapUsed|Realm, Worker, Instance|The percentage of swap memory used on the worker. See [psutil.virtual_memory()](https://psutil.readthedocs.io/en/latest/).|
|PercentTmpDiskUsed|Realm, Worker, Instance|The percentage of disk space used for the lava temporary area on the worker.|
|WorkerThreadsAlive|Realm, Worker, Instance|The number of job worker threads that are alive. The worker thread pool size is dependent on the configuration of a particular worker daemon. This is typically controlled in the [realms table](#the-realms-table).|
|WorkerThreadsDead|Realm, Worker, Instance|The number of job worker threads that have died. If not enough worker threads are active, job delays can increase.|

### CloudWatch Alarms

The CloudFormation worker template optionally creates the following CloudWatch
alarms:

*   A heartbeat alarm if the worker heartbeat message is not detected in the
    `/var/log/messages` CloudWatch log group for 5 minutes. This relies on the
    worker being configured to generate a heartbeat message every 60 seconds and
    the node being configured to replicate syslog messages to CloudWatch.

*   An SQS queue depth alarm if the `ApproximateNumberOfMessagesVisible` metric
    exceeds a value specified as a CloudFormation stack parameter. This alarm
    can indicate a dead or overloaded worker.

The target for the alarms is an SNS topic specified as a CloudFormation stack
parameter.

### Getting Internal Worker State Information { data-toc-label="Getting Internal Worker State" }

It is possible to get the worker to reveal some of its internal state by sending
it a SIGUSR1 (signal number 30). The information is written to the logger.
Typically, this is sent to **syslog**.

