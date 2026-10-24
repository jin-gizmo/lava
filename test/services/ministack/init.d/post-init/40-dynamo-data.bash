#!/bin/bash

# ------------------------------------------------------------------------------
# Add any setup DynamoDB entries
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

function sqs_queue_exists {
	aws sqs get-queue-url --queue-name "$1" > /dev/null 2>&1
}

function require {
	for i
	do
		[ "${!i}" = "" ] && error "$i must be set" && exit 1
	done
}

# AWS CLI v1 is provided on the ministack image which is Alpine based (grrrr).
# AWS doesn't support v2 on Alpine (and who can blame them).
# Also, on the ministack image, the CLI with some AWS services (e.g. sqs) does
# not honour the endpoint_url entry in ~/.aws/config. So we need to explicitly
# set endpoint-url on every aws command.

_AWS="$(command -v aws)"
function aws {
	"$_AWS" --endpoint-url "$AWS_ENDPOINT_URL" "$@"
}


# ------------------------------------------------------------------------------
# Convert JSON or YAML formatted raw data into DynamoDB style JSON.
function marshal_dynamo {
	python3 -c '
import json, sys, yaml
from decimal import Decimal
from boto3.dynamodb.types import TypeSerializer

def convert_floats(obj):
    if isinstance(obj, float):
        return Decimal(str(obj))
    if isinstance(obj, dict):
        return {k: convert_floats(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [convert_floats(v) for v in obj]
    return obj

data = convert_floats(yaml.safe_load(sys.stdin))
serializer = TypeSerializer()
marshalled = {k: serializer.serialize(v) for k, v in data.items()}
print(json.dumps(marshalled, indent=4))
'
}

# ------------------------------------------------------------------------------

require AWS_ENDPOINT_URL
require LAVA_REALM LAVA_WORKER
set -e
shopt -s nullglob
shopt -s globstar

TMP=$(mktemp -d)
trap '/bin/rm -rf $TMP' 0

# ------------------------------------------------------------------------------
info "Creating initial DynamoDB entries (idempotent)"
for d in /lava/data/dynamodb/* /host/data/dynamodb/*
do
	[ ! -d "$d" ] && continue
	debug "DynamoDB data dir: $d"
	# Inject the realm name into the target table name
	# shellcheck disable=SC2016
	table_name=$(basename "$d" | envsubst '${LAVA_REALM}')
	debug "Table $table_name"

	for f in "$d"/**/*.{json,yaml}
	do
		debug "Data file: $f"
		tmpf=$TMP/$(basename "$f")
		envsubst < "$f" | marshal_dynamo > "$tmpf"
		aws dynamodb put-item --table-name "${table_name}" --item "file://$tmpf"
		ok "Loaded $f"
	done
done
