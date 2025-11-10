#!/bin/bash
# ex: sw=4 ts=4 et ai

# ------------------------------------------------------------------------------
# Install the Redshift CA bundle
# ------------------------------------------------------------------------------

set -e

mkdir -p /usr/local/lib/redshift
cd /usr/local/lib/redshift

wget https://s3.amazonaws.com/redshift-downloads/amazon-trust-ca-bundle.crt
