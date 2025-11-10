
## The Realms Table { data-toc-label="Realms" }

The realms table is named `lava.realms`. This is a global lava table and is the
only object shared across realms.

|Field|Type|Required|Description|
|-|-|-|-------------------------------------------------------------|
|config|Map|No|An optional map of configuration values that will be applied to all workers in the realm. Refer to [Lava Worker Configuration](#lava-worker-configuration) for more information.|
|on_fail|List[Map]|No|The default [on_fail actions](#job-actions) for jobs in the realm.|
|on_success|List[Map]|No|The default [on_success actions](#job-actions) for jobs in the realm.|
|realm|String|Yes|A unique identifier for the realm. Keep it simple.|
|s3_key|String|Yes|A KMS key identifier used when objects are written to S3 by a worker. Typically, either a key ARN or `alias/<KEY-NAME>`.|
|s3_payloads|String|Yes|A [location in S3](#lava-s3-locations) where payloads are stored for the realm in the form `s3://<BUCKET>/<PREFIX>.`|
|s3_temp|String|Yes|A [location in S3](#lava-s3-locations) where job outputs are stored for the realm in the form `s3://<BUCKET>/<PREFIX>.`|
|X-\*|String|No|Any fields beginning with `x-` or `X-` are ignored by lava. These can be used as required for other purposes (e.g. CI/CD, versioning or other related purposes). A number of these fields are used as part of the boot process for EC2 based lava workers for configuration control.|
|\*|\*|\*|Other fields in the realms table may be present to set defaults for other lava subcomponents. These are described in the relevant section.|
