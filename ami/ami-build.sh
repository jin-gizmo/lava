#!/bin/bash
# ex: sw=4 ts=4 et ai

# ------------------------------------------------------------------------------
# Core build script for lava AMI.
#
# The following environment vars must be set:
#
#     OS:           Must match the ID / VERSION_ID combo from /etc/os-release
#                   (e.g. amzn2)
#     REPO_UPGRADE: Used to specify what updates happen on boot.
#     TIMEZONE:     Preferred timezone for instances
#     S3BUCKET:     S3 bucket containing extra (usually large) resource files.
#     S3PREFIX:     Prefix in S3 bucket containing extra resource files. This
#                   should end with a /
#                   
#
# At this point we assume the resources have been uploaded to ~/packer.
# ------------------------------------------------------------------------------

set -e

# ------------------------------------------------------------------------------
# Workout what OS we are on to ensure we have matching build.
. /etc/os-release

[ "${ID}${VERSION_ID}" != "$OS" ] && \
    echo "OS mismatch. Build is $OS and node is ${ID}${VERSION_ID} - abort" && exit 1

# ------------------------------------------------------------------------------
# Run all the configurators -- as root

cd ~/packer

for f in conf.d/[0-9]*
do
    echo
    echo "********************************************************************************"
    echo "** Running $f **" >&2
    echo "********************************************************************************"
    echo
    sudo --preserve-env "$f"
    status=$?
    echo
    echo "** Exit status: $status **" >&2
    echo
done

# ------------------------------------------------------------------------------
# Setup the local environment - skeleton for ec2-user.
(
    cd resources/etc/skel
    find . | cpio -pduv ~
)

exit 0
