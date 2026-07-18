
## Lava JSON Schemas

JSON schema definitions are available for the following lava artefacts:

*   [job specifications](#the-jobs-table)
*   [connection specifications](#the-connections-table)
*   [s3trigger specifications](#the-s3triggers-table)
*   [realm specifications](#the-realms-table)
*   [lava Amazon EventBridge rule specifications](#creating-amazon-eventbridge-rules).

The schemas are used for various purposes, including:

*   Validation of deployed artefacts and local files using the
    [lava-schema](#lava-schema-utility) utility
*   Pre-install checks in the [lav-job-framework](#the-lava-job-framework)
*   Syntax support in IDEs such as the JetBrains suite and VS Code.

!!! note
    The obvious omission from this list is the lava worker itself. The worker
    does not (currently) use the JSON schemas for validation. It generally takes
    a slightly more permissive approach to validation. Do not rely on this act
    of tolerance. Stick to the schemas.

The latest version of the JSON schemas are hosted on GitHub in both YAML and
JSON formats.

=== "YAML"
    | Object Type | Schema URL |
    | - | - |
    | [Job specification](#the-jobs-table) | [https://jin-gizmo.github.io/lava/schemas/latest/job.schema.yaml](schemas/latest/job.schema.yaml){:target="_blank" rel="noopener noreferrer"} |
    | [Connection specification](#the-connections-table) | [https://jin-gizmo.github.io/lava/schemas/latest/connection.schema.yaml](schemas/latest/connection.schema.yaml){:target="_blank" rel="noopener noreferrer"} |
    | [S3trigger specification](#the-s3triggers-table) | [https://jin-gizmo.github.io/lava/schemas/latest/s3trigger.schema.yaml](schemas/latest/s3trigger.schema.yaml){:target="_blank" rel="noopener noreferrer"} |
    | [Realm specification](#the-realms-table) | [https://jin-gizmo.github.io/lava/schemas/latest/realm.schema.yaml](schemas/latest/realm.schema.yaml){:target="_blank" rel="noopener noreferrer"} |
    | [EventBridge rule specification](#creating-amazon-eventbridge-rules) | [https://jin-gizmo.github.io/lava/schemas/latest/event-rule.schema.yaml](schemas/latest/event-rule.schema.yaml){:target="_blank" rel="noopener noreferrer"} |

=== "JSON"
    | Object Type | Schema URL |
    | - | - |
    | [Job specification](#the-jobs-table) | [https://jin-gizmo.github.io/lava/schemas/latest/job.schema.json](schemas/latest/job.schema.json){:target="_blank" rel="noopener noreferrer"} |
    | [Connection specification](#the-connections-table) | [https://jin-gizmo.github.io/lava/schemas/latest/connection.schema.json](schemas/latest/connection.schema.json){:target="_blank" rel="noopener noreferrer"} |
    | [S3trigger specification](#the-s3triggers-table) | [https://jin-gizmo.github.io/lava/schemas/latest/s3trigger.schema.json](schemas/latest/s3trigger.schema.json){:target="_blank" rel="noopener noreferrer"} |
    | [Realm specification](#the-realms-table) | [https://jin-gizmo.github.io/lava/schemas/latest/realm.schema.json](schemas/latest/realm.schema.json){:target="_blank" rel="noopener noreferrer"} |
    | [EventBridge rule specification](#creating-amazon-eventbridge-rules) | [https://jin-gizmo.github.io/lava/schemas/latest/event-rule.schema.json](schemas/latest/event-rule.schema.json){:target="_blank" rel="noopener noreferrer"} |
