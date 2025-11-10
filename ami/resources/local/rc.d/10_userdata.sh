#!/bin/bash

# Dump user data to syslog.

PROG=$(basename "$0")
log_facility=local0
log_tag=rclocal.userdata

# ------------------------------------------------------------------------------
# Get ec2 meta data
function meta {
    d=$(ec2-metadata --"$1" | sed -e '1s/^[^:]*: *//')
    [ "$d" == "not available" ] && return 1
    echo "$d"
}

# ------------------------------------------------------------------------------
logger -t "$log_tag" -p "${log_facility}.info" "$PROG: $(meta user-data)"
