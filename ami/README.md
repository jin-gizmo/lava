# The Lava AMI

> See **Building the Lava AMI** in the Lava User Guide for build instructions.

The Lava AMI is a dedicated AMI for running lava based on the Amazon Linux base
image. The intent is to reduce the installation burden on lava workers at
creation time, particularly for third party binary components such as Oracle.

The Lava AMI does not come with lava installed. That is expected to be installed
at instance boot time. The reason for this is that its a lot easier to drop a
new lava build into S3 and reboot a worker rather than having to build a new AMI
then update the EC2 launch configuration via CFN and then replace the worker
(and the same again for a rollback).

It was originally based on the Jindabyne SAK (Swiss Army Knife) AMI.

> Some of the components are rather old now and you would certainly do things a
> bit differently if starting from scratch (e.g. awsmetric would be very
> different). But it works and has proven to be robust over years of operation.
