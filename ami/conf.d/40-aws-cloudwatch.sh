#!/bin/bash
# ex: sw=4 ts=4 et ai

# ------------------------------------------------------------------------------
# Install Amazon CloudWatch Agent to log to CloudWatch
# ------------------------------------------------------------------------------

set -e

CW_DIR=/opt/aws/amazon-cloudwatch-agent
z=1
TMPDIR=$(mktemp -d)
trap '/bin/rm -rf $TMPDIR; exit $z' 0

yum install amazon-cloudwatch-agent -y

cp resources/amazon-cloudwatch-agent/config.json $CW_DIR/etc/config.json
chmod 644 $CW_DIR/etc/config.json

$CW_DIR/bin/amazon-cloudwatch-agent-ctl -a fetch-config -m ec2 -c file:$CW_DIR/etc/config.json -s

z=0
