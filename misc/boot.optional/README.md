# Optional Lava Worker Boot Scripts

This directory contains lava worker boot scripts that are not required by the
lava AMI but may be required by other AMIs (e.g. SAK). They get run from S3 by
the standard lava worker boot script (root.boot.sh).

If required, these need to be deployed under the _boot_ prefix in the lava code
area.

Each script must accept these arguments, even if it doesn't need them:

-   s3-source-area
-   realm
-   worker

Scripts that exit with status 1 will abort the main boot script. Any other exit
status will allow the main boot script to continue.

> The boot process is smart enough to not try to run this README file.
