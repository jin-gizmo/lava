
## The Events Table { data-toc-label="Events" }

The events table for a given `<REALM>` is named `lava.<REALM>.events`. It is
populated by lava workers as they start and finish jobs runs.

Querying the table via the DynamoDB console can be a bit tedious so a
utility `lava-events` is provided to assist with this. Get help thus:

```bash
lava-events --help
```

The [lava GUI](#the-lava-gui) also provides the ability to query
the events table.

|Field|Type|Required|Description|
|-|-|-|-------------------------------------------------------------|
|hostname|String|Yes|The hostname of the worker that ran the job.|
|instance\_id|String|No|The AWS EC2 instance ID. Not present when the worker is not an EC2 instance.|
|job\_id|String|Yes|The unique job identifier for the realm.
|log|List[Map]|Yes|A list of events that have occurred for this run of the job. Each entry in the list is a map which will contain `info`, `status` and `ts_event` fields. The contents of the `info` field are job type dependent.|
|run\_id|String|Yes|The UUID for the job run. This is used in the naming of job outputs.|
|status|String|Yes|The most recent `status` value for this job run. It will reflect the `status` value of the latest entry in the `log` list.|
|ts\_dispatch|String|Yes|A timezone aware ISO 8601 format timestamp for the time the job was dispatched.|
|ts\_event|String|Yes|A timezone aware ISO 8601 format timestamp for the most recent event for this job run. It will reflect the `ts_event` value for this job run.|
|ttl|Number|Yes|The epoch timestamp when the event record will expire. DynamoDB manages expiry automatically provided the TTL attribute for the table is set to `ttl`.|
|tu\_event|String|Yes|A timezone naive ISO 8601 format timestamp for the UTC time for the most recent event for this job run. It will reflect the `tu_event` value for this job run.
|worker\_id|String|No|If the worker is an AWS EC2 instance, the instance ID.|
|worker|String|Yes|The name of the worker that ran the job.|
