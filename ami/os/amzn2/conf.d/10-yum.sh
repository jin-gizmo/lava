#!/bin/bash
# ex: sw=4 ts=4 et ai

# ------------------------------------------------------------------------------
# Basic yum update / setup. Internet access required.
#
# Don't install optional packages here. Do that in 15-packages.sh
# ------------------------------------------------------------------------------

set -e

yum update -y

# ------------------------------------------------------------------------------
# Set REPO_UPGRADE to none for instances in tight VPCs.

# [ "$REPO_UPGRADE" = "" ] && REPO_UPGRADE=security
[ "$REPO_UPGRADE" = "" ] && REPO_UPGRADE=none

echo "REPO_UPGRADE is $REPO_UPGRADE"
sed --in-place=.orig "s/^repo_upgrade:.*/repo_upgrade: $REPO_UPGRADE/" /etc/cloud/cloud.cfg
