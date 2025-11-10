## Lava Backup Utility { data-toc-label="lava-backup" }

**Lava-backup** performs a complete extract of all of the configuration tables
for a given realm and stores the result in a zip file, either locally or in AWS
S3.

??? "Usage"

    ```bare
    usage: lava-backup [options] realm zip-file

    Backup the DynamoDB entries for a specified lava realm. The output is a zip file.

    positional arguments:
      realm               Realm name.
      zip-file            Name of the output zip file. Can be on the local machine
                          or in S3 (s3://....). 

    optional arguments:
      -h | --help         Print help and exit.
      -y | --yaml         Output the entries in YAML format. The default is JSON.
    ```

**Lava-backup** uses the [lava-dump](#lava-dump-utility) utility under the
covers. It can be run as a lava [cmd](#job-type-cmd) job if required. A lava
job specification suitable for backing up the current realm is:

```json
{
  "description": "Backup the DynamoDB entries for the realm",
  "dispatcher": "Sydney",
  "enabled": true,
  "job_id": "lava/dynamo-backup",
  "owner": "lava",
  "parameters": {
    "args": [
      "{{realm.realm}}",
      "{{realm.s3_temp}}/lava/dynamo-backup/{{ustart.strftime('%Y-%m-%d')}}.zip"
    ]
  },
  "payload": "lava-backup",
  "schedule": "0 19 * * *",
  "type": "cmd",
  "worker": "core"
}
```

!!! note
    Dispatcher, worker and schedule will need to be adjusted in the example.

