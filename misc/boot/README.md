# Lava Worker Boot Scripts

This directory contains lava worker boot scripts that get run from S3 by the
standard lava worker boot script (root.boot.sh). One of them must install lava
itself.

These need to be deployed under the _boot_ prefix in the lava code area.
They should all be installed.

It is expected that some environments may require additional, environment
specific scripts to install other things (e.g. vulnerability scanners etc.)

Each script must accept these arguments, even if it doesn't need them:

-   s3-source-area
-   realm
-   worker

Scripts that exit with status 1 will abort the main boot script. Any other exit
status will allow the main boot script to continue.

> The boot process is smart enough to not try to run this README file.


