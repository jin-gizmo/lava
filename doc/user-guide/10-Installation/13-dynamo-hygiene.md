
## Maintaining DynamoDB Table Entries { data-toc-label="Maintaining DynamoDB Entries" }

Lava comes with a number of mechanisms to assist with maintaining the health of
the entries in the [DynamoDB tables](#dynamodb-tables). These include:

*   The **[lava job framework](#the-lava-job-framework)** which provides a
    standardised template for creating, configuring and deploying lava jobs and
    associated components. It also provides support for automatic generation of
    checksums on table entries and
    [configuration drift detection](#configuration-drift-detection).

*   **Deep Schema validation** via the [lava-schema](#lava-schema-utility)
    utility.

*   **Bad practice detection** via the [lava-check](#lava-check-utility) utility.

*   **Checksum generation and validation** for DynamoDB table entries via the
    [lava-checksum](#lava-checksum-utility) utility and the
    [lava job framework](#the-lava-job-framework).

