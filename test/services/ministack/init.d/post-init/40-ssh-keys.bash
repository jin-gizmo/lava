#!/bin/bash

# ------------------------------------------------------------------------------
# Load SSH key(s) as SSM parameters.
#
# Files ending in .pub are assumed to be public and are stored as string
# parameters. All other files are assumed to be secret keys and are stored as
# secure string parameters.
# ------------------------------------------------------------------------------

# DEBUG=yes

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

# ------------------------------------------------------------------------------

require AWS_ENDPOINT_URL LAVA_REALM

set -e
shopt -s nullglob
shopt -s globstar

for key_file in /lava/data/ssh/**/* /host/data/ssh/**/*
do
	debug "Processing $key_file"
	if [[ "$key_file" == *.pub ]]
	then
		varname=$(basename "${key_file%.*}")
		varname="/lava/${LAVA_REALM}/ssh/${varname}/public"
		put_args=(
			--type String
			--description "SSH public key"
		)
	else
		# No .pub suffix -- assume this is a secret key
		varname=$(basename "${key_file}")
		varname="/lava/${LAVA_REALM}/ssh/${varname}/secret"
		put_args=(
			--type SecureString
			--description "SSH secret key"
			--key-id "alias/lava-${LAVA_REALM}-sys"
		)
		
	fi

	aws ssm put-parameter --overwrite "${put_args[@]}" \
		--name "$varname" --value "file://$key_file" > /dev/null
	ok "Loaded $key_file to SSM as $varname"
done

exit 0

