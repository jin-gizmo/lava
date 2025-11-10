#!/bin/bash
# ex: sw=4 ts=4 et ai

# ------------------------------------------------------------------------------
# Set the AWS region in a config file compatible with AWS CLI.
# ------------------------------------------------------------------------------

declare -a BACKOFF=(0 5 5 10 10 30)

PROG=$(basename "$0")
log_facility=local0
log_tag=rclocal.aws_region

# ------------------------------------------------------------------------------
function error {
        [ -t 2 ] && echo "$PROG: ERROR: $*" >&2
        logger -t "$log_tag" -p "${log_facility}.error" "ERROR: $*"
}

function warning {
        [ -t 2 ] && echo "$PROG: WARNING: $*" >&2
        logger -t "$log_tag" -p "${log_facility}.warning" "WARNING: $*"
}

function info {
        [ -t 2 ] && echo "$PROG: INFO: $*" >&2
        logger -t "$log_tag" -p "${log_facility}.info" "INFO: $*"
}

function abort {
        error "$*"
        exit 1
}

# ------------------------------------------------------------------------------
# Get ec2 meta data
function meta {
    d=$(ec2-metadata --"$1" | sed -e '1s/^[^:]*: *//')
    [ "$d" == "not available" ] && return 1
    echo "$d"
}

# ------------------------------------------------------------------------------
# IMDS (v2 in particular) can take a while to become available and, if it's not,
# we're in serious trouble. So we have a retry and backoff.
for backoff in "${BACKOFF[@]}"
do
    [ "$backoff" -ne 0 ] && warning "Retrying in $backoff seconds"
    sleep "$backoff"
    az=$(meta availability-zone)
    [ $? -ne 0 ] && warning "Could not get availability zone - not available" && continue
    [[ ! "$az" =~ ^[a-z]{2}(-[a-z]+)?-[a-z]+-[0-9]+[a-z]$ ]] && warning "Availability zone malformed - $az" && continue
    region="${az%?}"
    break
done

[ "$region" == "" ] && abort Could not get AWS region -- this is really, really bad

info "Setting region to $region"

mkdir -p /usr/local/etc/aws
cat > /usr/local/etc/aws/config <<!
[default]
region = $region
metadata_service_num_attempts=5
metadata_service_timeout=5
s3 =
    signature_version = s3v4
!

chmod 644 /usr/local/etc/aws/config
