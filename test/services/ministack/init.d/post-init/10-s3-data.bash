#!/bin/bash

# ------------------------------------------------------------------------------
# Copy static data to S3. Any created buckets are made private.
# ------------------------------------------------------------------------------

# DEBUG=yes
DEBUG=

# ------------------------------------------------------------------------------
function info {
	echo "🔵 $*"
}
function ok {
	echo "✅ $*"
}
function error {
	echo "❌ $*"
}
function debug {
	[ "$DEBUG" = "" ] && return 0
	echo "🟪 $*"
}

function require {
	for i
	do
		[ "${!i}" = "" ] && error "$i must be set" && exit 1
	done
}

function bucket_exists {
	aws s3api head-bucket --bucket "$1" > /dev/null 2>&1
}

# ------------------------------------------------------------------------------
require AWS_ENDPOINT_URL

set -e

shopt -s nullglob

for d in /lava/data/s3/* /host/data/s3/*
do
	[ ! -d "$d" ] && continue
	debug "Checking $d for transfer to S3"
	bucket=$(basename "$d" | envsubst '${LAVA_REALM}')
	debug "Bucket=$bucket"
	if ! bucket_exists "$bucket"
	then
		info "Creating S3 bucket \"$bucket\""
		aws s3 mb "s3://$bucket"
		aws s3api put-public-access-block \
			--bucket "$bucket" \
			--public-access-block-configuration BlockPublicAcls=TRUE,IgnorePublicAcls=TRUE,BlockPublicPolicy=TRUE,RestrictPublicBuckets=TRUE
	fi
	info "Copying data to s3://$bucket"
	( cd "$d" && aws s3 cp --only-show-errors --rec . "s3://$bucket" )
done

