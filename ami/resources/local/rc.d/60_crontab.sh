#!/bin/bash

# Get a "crontab" key from userdata JSON and use that to populate crontabs for
# various users. Other keys are ignored. Must run as root.
#
# Individual crontab files must be objects in S3.
#
# Sample userdata:
#
#    {
#        "crontab": {
#            "ec2-user": "s3://mybucket/ec2-user.crontab",
#            "root": "s3://another.bucket/crontab-for-root"
#        }
#    }

PROG=$(basename "$0")
export PATH=$PATH:/usr/local/bin
log_facility=local0
log_tag=rclocal.crontab

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

# ------------------------------------------------------------------------------
# Usage: install_crontab user s3-object-containing-crontab

function install_crontab {
	user="$1"
	crontab="$2"
	crontmp="/tmp/$1.crontab"

	[[ ! "$crontab" =~ ^s3://.* ]] \
		&& error "Bad crontab object for user $user - S3 source object name must start with s3://" \
		&& return 2

	# Fetch the config file from S3
	err=$(aws s3 --region "$region" cp "$crontab" "$crontmp" 2>&1)
	[ $? -ne 0 ] && error "Could not get $crontab from S3: $err" && return 1

	# Install it 
	err=$(crontab -u "$user" "$crontmp" 2>&1)
	[ $? -ne 0 ] && error "Could not install crontab for user $user: $err" && return 1

	/bin/rm -f "$crontmp"

	info "Crontab for user $user installed ok"
	return 0
}

# ------------------------------------------------------------------------------
region=$(meta availability-zone | sed s/.$//)
[ "$region" == "" ] && abort "Cannot get region. Is this an EC2 instance?"

# Get userdata and look for a key containing the crontab info
userdata=$(meta user-data)
[ $? -ne 0 ] && abort "Cannot get userdata. Is this an EC2 instance?"

crontab=$(echo "$userdata" | kex --ignore --type json crontab 2>&1)
[ $? -ne 0 ] && abort "Bad userdata: $crontab"

[ "$crontab" == "" ] && exit 0

# crontab variable should consist of lines "user=s3-object-name" from kex
echo "$crontab" | (
	status=0
	IFS='='
	while read -r line
	do
		# shellcheck disable=SC2086
		set -- $line
		if [ $# -eq 2 ]
		then
			install_crontab "$1" "$2"
			[ $? -ne 0 ] && status=1
		else
			error "Could not process crontab spec for user $1 - skipping"
			status=1
		fi
	done
	exit $status
)
