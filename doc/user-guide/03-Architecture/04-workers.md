
## Lava Workers

A lava worker is any Linux node running the worker code bundle. The worker
is multi-threaded and can be run interactively, in batch mode or as a daemon.

One Linux instance can run multiple workers from the same or different worker
fleets, if required. While it is possible to run workers from different realms on
the one AWS EC2 instance, this is not recommended as it means the different
realms would be sharing an IAM instance role.

The [CloudFormation templates](#lava-installation-and-operation)
create a launch template and auto scaling group for each worker fleet based on
the [lava EC2 AMI](#the-lava-ec2-ami). The worker will install the lava code
from S3 and run it on boot.
