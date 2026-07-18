#!/bin/bash

# ------------------------------------------------------------------------------
# Set up some auxiliary infrastructure bits and pieces.
# ------------------------------------------------------------------------------

REALM="test"
WORKER=core
# We don't need the lava bucket in here -- the CFN creates that.
BUCKETS=(aux cfn code log events)
# Ministack doesn't actually do S3 bucket logging but it does support the API
# calls that configure it. This is important for some tests.
ENDPOINT_URL=http://localhost:4566

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

function cfn_stack_exists {
	aws cloudformation describe-stacks --stack-name "$1" > /dev/null 2>&1
}

function sqs_queue_exists {
	aws sqs get-queue-url --queue-name "$1" > /dev/null 2>&1
}

function require {
	for i
	do
		[ "${!i}" = "" ] && error "$i must be set" && exit 1
	done
}

# ------------------------------------------------------------------------------
require AWS_ENDPOINT_URL

set -e

info "Creating some standard S3 buckets (idempotent)"
for b in "${BUCKETS[@]}"
do
	aws s3 mb "s3://$b"
done

# Create an empty file in aux bucket for tests to use.
aws s3 cp - s3://aux/sentinel < /dev/null
