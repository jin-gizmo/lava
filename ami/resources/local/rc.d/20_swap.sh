#!/bin/bash

# Configure a swap file. A swap file is only ever setup once but will persist
# after reboots.
#
# Sample userdata:
#
#    {
#        "swap": {
#            "size": "3",
#            "file": "/swapfile"
#        }
#    }
#
# The size field is the swap file size in Gibibytes (1024 * 1024 * 1024 bytes).
# If 0 or not specified, swapping is not enabled. There are no real protections
# against stupidity here (i.e. creating a swap too big or too small).
#
# The file field is the name of the swap file. The default is /swapfile.
# ------------------------------------------------------------------------------

PROG=$(basename "$0")
export PATH=$PATH:/usr/local/bin

log_facility=local0
log_tag=rclocal.userdata

# ------------------------------------------------------------------------------
function error {
	echo "$PROG: ERROR: $*" >&2
	logger -t "$log_tag" -p "${log_facility}.error" "ERROR: $*"
}

function warning {
	echo "$PROG: WARNING: $*" >&2
	logger -t "$log_tag" -p "${log_facility}.warning" "WARNING: $*"
}

function info {
	echo "$PROG: INFO: $*" >&2
	logger -t "$log_tag" -p "${log_facility}.info" "INFO: $*"
}

function abort {
	error "$*"
	exit 1
}

# Get ec2 meta data
function meta {
    d=$(ec2-metadata --"$1" | sed -e '1s/^[^:]*: *//')
    [ "$d" == "not available" ] && return 1
    echo "$d"
}


function ec2-userdata {
	local ud
	ud=$(ec2-metadata --user-data)
	[ $? -ne 0 -o "$ud" == "user-data: not available" ] && return 1
	echo "$ud"
}


# ------------------------------------------------------------------------------
# Get userdata and look for a key containing the swap info
userdata=$(meta user-data)
[ $? -ne 0 ] && abort "Cannot get userdata. Is this an EC2 instance?"

size=$(echo "$userdata" | kex --ignore --type json swap.size 2>&1)
[ $? -ne 0 ] && abort "Bad userdata: $size"
swapfile=$(echo "$userdata" | kex --ignore --type json swap.file 2>&1)
[ $? -ne 0 ] && abort "Bad userdata: $swapfile"

[ "$size" == "" ] && size=0
[ "$swapfile" == "" ] && swapfile=/swapfile

[[ "$size" =~ ^[0-9]+$ ]] || abort "Bad swap size: $size"
[[ "$swapfile" =~ ^/[.a-zA-Z0-9_-]+$ ]] || abort "Bad swap file: $swapfile"

[ "$size" -eq 0 ] && info "Swap not required" && exit 0
[ -f "$swapfile" ] && info "Swap is already configured" && exit 0

# ------------------------------------------------------------------------------

dd if=/dev/zero of="$swapfile" bs=1M count=$((size*1024)) \
	|| abort "Could not created swap file $swapfile"
info "Created swap file $swapfile"

chmod 600 "$swapfile"
mkswap "$swapfile"
swapon "$swapfile"
echo "$swapfile swap swap defaults 0 0" >> /etc/fstab
info "Swapping configured on $swapfile"

swapon --show | logger -t "$log_tag" -p "${log_facility}.info"
