#!/bin/bash
# ex: sw=4 ts=4 et ai

# ------------------------------------------------------------------------------
# RDS utilities, certs etc
# ------------------------------------------------------------------------------

set -e

. lib/funcs.sh

mkdir -p /usr/local/lib/rds
cd /usr/local/lib/rds

wget https://truststore.pki.rds.amazonaws.com/global/global-bundle.pem
wget https://s3.amazonaws.com/rds-downloads/rds-ca-2019-root.pem
wget https://s3.amazonaws.com/rds-downloads/rds-combined-ca-bundle.pem

# Get regional certs -- Don't worry about download errors
set +e
for region in $(aws ec2 describe-regions --output text --query 'Regions[].RegionName' --all-regions)
do
    if wget "https://s3.amazonaws.com/rds-downloads/rds-ca-2019-${region}.pem"
    then
        info "Downloaded RDS cert for $region"
    else
        warning "Could not get RDS cert for $region"
    fi
done
