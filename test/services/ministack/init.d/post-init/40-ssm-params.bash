#!/bin/bash

# ------------------------------------------------------------------------------
# Add SSM parameters. These are loaded by the ssmp utility. The input data is
# a YAML file containing parameter specs.
# ------------------------------------------------------------------------------

# Length of random strings made available to ssmp
RAND_LEN=24

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
shopt -s globstar

TMP=$(mktemp -d)
trap '/bin/rm -rf $TMP' 0

# ------------------------------------------------------------------------------
# Create some random strings that can be used in parameters, The _0 .. _9 ones
# are for the user. The _x0 ... _x9 ones are intended system internal use.
for i in {0..9} x{0..9}
do
	v=$(openssl rand -base64 $RAND_LEN)
	export "SSMP_RAND${RAND_LEN}_$i=$v"
done

# ------------------------------------------------------------------------------
info "Loading SSM parameters"
for f in /lava/data/ssm/**/*.yaml /host/data/ssm/**/*.yaml /run/data/ssm/**/*.yaml
do
	(
		# cd allows ssmp to pick up the .env for this group of files.
		cd "$(dirname "$f")" || exit 1
		ssmp load --path "/lava/${LAVA_REALM}" \
			--input "$f" --force \
			--env-var 'LAVA_*' \
			--env-var 'AWS_*REGION'
	)
	ok "Loaded $f"
done
