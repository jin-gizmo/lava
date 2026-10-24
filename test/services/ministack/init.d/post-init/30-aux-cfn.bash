#!/bin/bash

# ------------------------------------------------------------------------------
# Run any additional CloudFormation templates in s3://cfn
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

function cfn_stack_exists {
	aws cloudformation describe-stacks --stack-name "$1" > /dev/null 2>&1
}

function require {
	for i
	do
		[ "${!i}" = "" ] && error "$i must be set" && exit 1
	done
}

# ------------------------------------------------------------------------------
require AWS_ENDPOINT_URL LAVA_REALM

set -e

shopt -s nullglob

TMP=$(mktemp -d)
trap '/bin/rm -rf $TMP' 0

# ------------------------------------------------------------------------------
info "Deploying auxiliary CFN stacks"
for cfn in /lava/data/s3/cfn/*.cfn.{json,yaml}
do
	base=$(basename "$cfn")  # xyz.cfn.json
	stack="${base%.cfn.*}"   # xyz
	stem="${base%.*}"        # xyz.cfn
	if cfn_stack_exists "$stack"
	then
		ok "Stack \"$stack\" already exists -- leaving as is"
		continue
	fi
	create_stack_args=(
		--stack-name "$stack"
		--template-url "http://s3.amazonaws.com/cfn/$base"
	)
	if [ -f "/lava/conf/${stem}.cli.json" ]
	then
		envsubst < "/lava/conf/${stem}.cli.json" > "$TMP/${stem}.cli.json"
		create_stack_args+=(--cli-input-json "file://$TMP/${stem}.cli.json")
	fi
	debug "Create Stack Args:" "${create_stack_args[@]}"
	aws cloudformation create-stack "${create_stack_args[@]}"
	info "Stack $stack: waiting for stack creation to complete"
	aws cloudformation wait stack-create-complete --stack-name "$stack"
	ok "Stack \"$stack\" created"

done
