

# ------------------------------------------------------------------------------
# Ministack setup to host a lava realm
# ------------------------------------------------------------------------------


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

require AWS_ENDPOINT_URL
require LAVA_REALM LAVA_WORKER
set -e
shopt -s nullglob

TMP=$(mktemp -d)
trap '/bin/rm -rf $TMP' 0

# Ministack doesn't actually do S3 bucket logging but it does support the API
# calls that configure it. This is important for some tests.
LOGGED_BUCKETS=(lava)
ENCRYPTED_BUCKETS=(lava)
BUCKET_KMS_KEY="alias/lava-${LAVA_REALM}-user"

# ------------------------------------------------------------------------------
info "Deploying Lambda code bundles"

# shellcheck disable=SC2086
if [ "$(echo /lava/lambda/*-${LAVA_VERSION}.zip)" = "/lava/lambda/*-${LAVA_VERSION}.zip" ]
then
	error "Could not find lambda code bundles for lava version $LAVA_VERSION"
	exit 1
fi

# shellcheck disable=SC2231
for f in /lava/lambda/*-${LAVA_VERSION}.zip
do
	aws s3 cp --no-progress "$f" s3://code/lava/_dist_/lambda/
done
aws s3 ls s3://code/lava/ --rec

# ------------------------------------------------------------------------------
info "Uploading CloudFormation templates"
for f in /lava/cfn/*.cfn.json
do
	target="$(basename "$f")"
	# We need to strip resources ministack can't handle in CFN.
	jq '.Resources |= with_entries(select(.value.Type != "AWS::IAM::Group"))' "$f" \
		| aws s3 cp - "s3://cfn/$target"
done
aws s3 ls s3://cfn --rec

realm_stack="lava-${LAVA_REALM}"
if cfn_stack_exists "$realm_stack"
then
	ok "Realm stack \"$realm_stack\" already exists -- leaving as is"
else
	envsubst < /lava/conf/realm-cfn-cli.json > "$TMP/realm-cfn-cli.json"
	info "Running the lava realm stack for \"${LAVA_REALM}\""
	# WE can't use --cli-input-yaml because ministack container has AWS CLI v1 :-(
	aws cloudformation create-stack \
		--stack-name "$realm_stack" \
		--template-url http://s3.amazonaws.com/cfn/lava-realm.cfn.json \
		--cli-input-json "file://$TMP/realm-cfn-cli.json"
	info "Waiting for stack creation to complete"
	aws cloudformation wait stack-create-complete --stack-name "$realm_stack"
	ok "Stack \"$realm_stack\" created"
fi
aws dynamodb list-tables --output table --query TableNames

# ------------------------------------------------------------------------------
# Add any setup DynamoDB entries
info "Creating initial DynamoDB entries (idempotent)"
for d in /lava/conf/dynamodb-data/*
do
	[ ! -d "$d" ] && continue
	for f in "$d"/*.json
	do
		aws dynamodb put-item --table-name "$(basename "$d")" --item "file://$f"
		ok "Loaded $f"
	done
done

# ------------------------------------------------------------------------------
# Ministack CloudFormation ignores bucket logging configuration. For some
# buckets this is important for some tests.
info "Configuring bucket logging"
for b in "${LOGGED_BUCKETS[@]}"
do
	aws s3api put-bucket-logging \
		--bucket "$b" \
		--bucket-logging-status "$(jq -n --arg b "$b" '{
		    LoggingEnabled: {
		      TargetBucket: "log",
		      TargetPrefix: ("s3/" + $b + "/"),
		      TargetObjectKeyFormat: {
		      PartitionedPrefix: {
		        PartitionDateSource: "EventTime"
		      }
		    }
		  }
		}')"
	info "    $b - done"
done
#
# ------------------------------------------------------------------------------
# Ministack CloudFormation ignores bucket encryption configuration. For some
# buckets this is important for some tests.
info "Configuring bucket encryption"
for b in "${ENCRYPTED_BUCKETS[@]}"
do
	aws s3api put-bucket-encryption \
		--bucket "$b" \
		--server-side-encryption-configuration "$(jq -n --arg key "$BUCKET_KMS_KEY" '{
		    Rules: [{
		      ApplyServerSideEncryptionByDefault: {
			SSEAlgorithm: "aws:kms",
			KMSMasterKeyID: $key
		      },
		      BucketKeyEnabled: true
		    }]
		  }')"
	info "    $b - done"
done

# ------------------------------------------------------------------------------
# Set up the worker queue. Default queue attributes are fine for testing.
# The alternative would be to try to run the worker CFN template but that's got
# heaps of stuff in there that is only required for EC2 based workers. All we
# really need is the worker SQS queue.

worker_queue="lava-${LAVA_REALM}-${LAVA_WORKER}"
if sqs_queue_exists "$worker_queue"
then
	ok "Worker SQS queue \"$worker_queue\" exists"
	# Make sure no detritus left in the queue from an earlier run.
	info "Purging SQS queue \"$worker_queue\""
	queue_url=$(aws sqs get-queue-url --output text --queue-name "$worker_queue")
	aws sqs purge-queue --queue-url "$queue_url"
	ok "SQS queue \"$worker_queue\" purged"
else
	info "Creating lava worker SQS queue"
	aws sqs create-queue --queue-name "$worker_queue"
	ok "SQS queue \"$worker_queue\" created"
fi

