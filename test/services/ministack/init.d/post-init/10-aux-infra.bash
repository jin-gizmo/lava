#!/bin/bash

# ------------------------------------------------------------------------------
# Set up some auxiliary infrastructure bits and pieces.
# ------------------------------------------------------------------------------

# We don't need the lava bucket in here -- the CFN creates that.
PRIVATE_BUCKETS=(aux cfn code log events)
# Ministack doesn't actually do S3 bucket logging but it does support the API
# calls that configure it. This is important for some tests.

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

shopt -s nullglob

info "Creating some standard S3 buckets (idempotent)"
for b in "${PRIVATE_BUCKETS[@]}"
do
	aws s3 mb "s3://$b"
	aws s3api put-public-access-block \
		--bucket "$b" \
		--public-access-block-configuration BlockPublicAcls=TRUE,IgnorePublicAcls=TRUE,BlockPublicPolicy=TRUE,RestrictPublicBuckets=TRUE
done

# Create an empty file in aux bucket for tests to use.
aws s3 cp - s3://aux/sentinel < /dev/null

# ------------------------------------------------------------------------------
info "Deploying auxiliary CFN stacks"
for cfn in /lava/conf/*.cfn.{json,yaml}
do
	base=$(basename "$cfn")
	stack="${base%.cfn.*}"
	if cfn_stack_exists "$stack"
	then
		ok "Stack \"$stack\" already exists -- leaving as is"
		continue
	fi
	aws s3 cp "$cfn" "s3://cfn/"
	aws cloudformation create-stack \
		--stack-name "$stack" \
		--template-url "http://s3.amazonaws.com/cfn/$base"
	info "Stack $stack: waiting for stack creation to complete"
	aws cloudformation wait stack-create-complete --stack-name "$stack"
	ok "Stack \"$stack\" created"

done
