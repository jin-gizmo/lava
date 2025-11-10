
## Example Usage of the State Manager { data-toc-label="Examples" }

Consider the following simple job that gets triggered by an object creation in
S3 (via s3trigger). The job simply counts the number of lines in the file and
stores the result as a state item with ID `sid`.

```json
{
  "description": "Count lines in file from S3",
  "enabled": true,
  "globals": {
    "bucket": "-- provided by s3trigger --",
    "key": "-- provided by s3trigger --"
  },
  "job_id": "demo/line-counter",
  "parameters": {
    "args": [
      "lava-state put sid -p lines=$(aws s3 cp 's3://{{globals.bucket}}/{{globals.key}}' - | wc -l)"
    ]
  },
  "payload": "/bin/sh -c",
  "type": "cmd",
  "worker": "core"
}

```

The resulting state item will look like this:

```json
{
  "publisher": "demo/line-counter",
  "state_id": "sid",
  "timestamp": "2022-03-26T12:18:04+11:00",
  "ttl": 1648343884,
  "type": "json",
  "value": "{\"lines\": \"45\"}"
}
  
```

Another job can access this state item in the job spec rendering process or in
the job logic itself. Here is an example of the former.

```json
{
  "description": "Print out how many lines there were",
  "dispatcher": "...",
  "enabled": true,
  "job_id": "demo/line-reporter",
  "payload": "echo The file contained {{state.sid}} lines",
  "state": {
    "sid": "-- default value to be replaced at run-time --"
  },
  "schedule": "...",
  "type": "cmd",
  "worker": "core"
}

```

Note that the state item that is required at run-time has to be declared (with a
default value) so that it can be obtained from the state table and made
available to the Jinja renderer.
