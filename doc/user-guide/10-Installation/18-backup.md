
## Backing Up Lava Configuration

When the lava [DynamoDB tables](#dynamodb-tables) are created using the realm
CloudFormation template, point-in-time recovery is configured for the main
configuration tables. DynamoDB maintains continuous backups of the tables for
the last 35 days.

Lava also comes with two additional utilities to facilitate bulk extraction and
backup of data from the lava tables.

*   [lava-dump](#lava-dump-utility) performs a bulk extract of data from a
    single table to a local directory. It can extract all entries with keys that
    match any of a list of GLOB style patterns. By default, all entries are
    extracted.

*   [lava-backup](#lava-backup-utility) performs a complete extract of all of
    the configuration tables for a given realm and stores the result in a zip
    file, either locally or in AWS S3. It can be run as a lava
    [cmd](#job-type-cmd) job if required.

