#!/bin/bash

# Deploy a whole bunch of lava artefacts to S3.

# This is pretty crappy. You know it. I know it. Feel free to dazzle everyone
# with your brilliance.


PROG=$(basename "$0")

# shellcheck disable=SC2155
export PATH=$(pwd)/etc:$PATH
aws=aws
config_file=deploy.yaml

version=$(python3 lava/version.py)

# ------------------------------------------------------------------------------
function usage {
	cat >&2 <<!
Deploy lava artefacts. The build must be done prior.

Usage: $PROG -e environment [-f deploy.yaml ] [-d] [-h] [-n] [component ...]

Args:
    -e environment	Target environment. The deploy.yaml file must contain a
    			key for this.

    -f deploy.yaml	Specify a YAML file containing S3 target locations. If
    			not specified, the default is deploy.yaml in the current
			directory.

    -d			Dry-run.

    -h			Print help and exit.

    -l			List deployable components and exit.

    -n			Same as -d like make(1).

    -v			Deploy the specified lava version. If not specified,
    			the latest version is deployed (currently $version).

    
    component		Only deploy the named components. If not specified, all
    			available components for which there is a a deployment
			configuration on the specification file will be deployed.

!
}

# ------------------------------------------------------------------------------
function info {
	if [ -t 1 ]
	then
		echo "[34m$*[0m"
	else
		echo "INFO: $*"
	fi
}

function warning {
	if [ -t 1 ]
	then
		echo "[35m⚠️  $*[0m"
	else
		echo "WARNING: $*"
	fi
}

function error {
	if [ -t 1 ]
	then
		echo "[31m❌ $*[0m"
	else
		echo "ERROR: $*"
	fi
}

function abort {
	if [ -t 1 ]
	then
		echo "[91m❌ $*[0m"
	else
		echo "ABORT: $*"
	fi
	exit 1
}

function ok {
	if [ -t 1 ]
	then
		echo "[32m✅ $*[0m"
	else
		echo "OK: $*"
	fi
}

# . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 
# Sync a single file to S3. This is a hack with some limitations caused by the
# need to put a wildcard at the beginning of the include pattern or it won't work.
# Usage: s3_sync_file src_file s3_location
function s3_sync_file {
	local dir file
	dir=$(dirname "$1")
	file=$(basename "$1")

	$aws s3 sync "$dir" "$2" --exclude '*' --include "*$file"
}

# . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 
# Get a config value for the current environment
function config {
	echo "{{${env}.$1}}" | jinja -f "$config_file" 2>/dev/null
}

# . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 
# Get a config value for the current environment where the value is list or dict
function config_list {
	echo "{{${env}.$1 | join(' ')}}" | jinja -f "$config_file" 2>/dev/null
}

# . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 
# Get an s3 location from the config file
function s3 {
	local v

	v=$(config "$1.s3")
	[ "$v" == "" ] && return 1

	# We allow env vars and lava version to be injected using normal shell syntax
	s3loc -/ "$v" "$s3base" | version="$version" envsubst
	
	# [[ "$v" == "s3://*" ]] && echo "$v" && return 0
	# [ "$s3base" == "" ] && abort "$1 not fully qualified and 's3.base' not set"
	# echo "s3://$s3base/$v"
}

# . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 
# Check if the first argument is present in the list of remaining args.
function contains {
	local v="$1"
	shift
	for i
	do
		[ "$i" = "$v" ] && return 0
	done
	return 1
}


# . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 
# Introspection to get all functions with names matching a regex.
function get_funcs_by_regex {
	declare -F | cut -d' ' -f3 | grep "$1" | sort 
}

# . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 
# Introspection to get a summary of all available deployment modules.
function list_deployers {

	get_funcs_by_regex '^deploy_' | while read -r fname
	do
		item="${fname#deploy_}"
		# Get the embedded description
		description=$(
			declare -f "$fname" | \
			sed -Ene '
				/[[:space:]]*:[[:space:]]*/{
					s/[[:space:]]*:[[:space:]]*(.*);$/\1/
					s/^"(.*)"/\1/
					p;q;
				}'
		)
		printf "%-10s %s\n" "$item" "$description"
	done
}


# ------------------------------------------------------------------------------
# These functions are the component deployers. The must all have names in the
# form "deploy_<COMPONENT>" where the <COMPONENT> part matches a key in the config
# file. The functions are auto discovered and the ": description" after the
# function header is important. The deployer can return the following status codes:
# 	0	Deployment was performed ok
# 	*	Anything else is assumed to mean the deployment failed.

# . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 
function deploy_pkg {
	: "Main lava code package."

	local target

	target=$(s3 pkg)
	[ "$target" = "" ] && return 0

	# Lava core code package
	set -- "dist/pkg/*/lava-$version-*.tar.bz2"
	if [ $# -ne 0 ]
	then
		info "Syncing lava worker package to $target"
		$aws s3 sync dist/pkg "$target" --exclude '*' --include "*lava-$version-*.tar.bz2"
	else
		warning "No lava code packages found"
	fi

}

# . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 
function deploy_boot {
	: "Lava worker boot scriptlets (not root.boot*)."

	local target src

	target=$(s3 boot)
	[ "$target" = "" ] && return 0

	src=misc/boot
	info "Syncing $src to $target"
	$aws s3 sync $src "$target" --include '*' --exclude 'README*' --exclude '.??*'
}

# . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 
function deploy_lambda {
	: "Lambda function code bundles."

	local target

	target=$(s3 lambda)
	[ "$target" = "" ] && return 0

	# shellcheck disable=SC2086
	set -- dist/lambda/*-$version.zip
	if [ $# -ne 0 ]
	then
		info "Syncing lambda functions to $target"
		$aws s3 sync dist/lambda "$target" --exclude '*' --include "*-$version.zip"
	else
		warning "No lambda code packages found"
	fi
}

# . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 
function deploy_cfn {
	: "CloudFormation Templates."
	local target

	target=$(s3 cfn)
	[ "$target" = "" ] && return 0

	src=dist/cfn
	$aws s3 sync dist/cfn/ "$target"
}

# . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 
function deploy_framework {
	: "Lava job framework (Deprecated in favour of lava-new)."
	local target src

	target=$(s3 framework)
	[ "$target" = "" ] && return 0

	src="dist/dev-tools/cookiecutter-lava-$version.zip"

	if [ -f "$src" ]
	then
		info "Syncing $src to $target"
		s3_sync_file "$src" "$target"
	else
		warning "$src not found"
	fi
}


# . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 
# ami: Components required to be in S3 to build the AMI (not the ami itself)
#      The AMI builder also does this sync process just in case.
function deploy_ami {
	: "Components required to be in S3 to build the AMI (not the AMI itself)."
	local target src

	target=$(s3 ami)
	[ "$target" = "" ] && return 0

	src=ami/resources.s3

	if [ -d "$src" ]
	then
		info "Syncing $src to $target"
		$aws s3 sync "$src" "$target" --exclude '*/.*'
	else
		warning "$src not found"
	fi
}

# ------------------------------------------------------------------------------
# Process args. 

# shellcheck disable=SC2048,SC2086
args=$(getopt c:de:f:hlnv: $*)
[ $? -ne 0 ] && usage && exit 1

# shellcheck disable=SC2086
set -- $args
while true
do
	case "$1"
	in
		-e)	env="$2"; shift 2;;
		-f)	config_file="$2"; shift 2;;
		-d | -n)
			dryrun=yes
			aws="echo aws"
			shift;;
		-h)	usage; exit 0;;
		-l)	list_deployers; exit 0;;
		-v)	version="$2"; shift 2;;
		--)	shift; break;;
		*)	abort "Internal error";;
	esac
done

[ "$env" = "" ] && usage && exit 1

# shellcheck disable=SC2046
read -ra deployers <<< $(get_funcs_by_regex '^deploy_')
# Get the array of requested components to deploy
components=("$@")
for c in "${components[@]}"
do
	contains "deploy_$c" "${deployers[@]}" || abort "No such component: $c"
done

[ ! -f "$config_file" ] && abort "$config_file: No such file"

[ "$(echo "{{$env}}" | jinja -f "$config_file")" == "" ] && abort "$env: No such environment in $config_file"


# ------------------------------------------------------------------------------

# Make sure we are aiming at the right AWS account. This is superfluous for the
# jinlava target but a good safety mechanism for the others deployers.
#
info "Verifying target account"
actual_account_id=$(aws sts get-caller-identity --query Account --output text) || \
	abort "Cannot get target account ID"
target_account_id=$(config account_id)
[ "$target_account_id" = "" ] && \
	abort "Target account ID not specified in $config_file for environment \"$env\""
[ "$actual_account_id" != "$target_account_id" ] && \
	abort "You are pointing at the wrong AWS account. Expected $target_account_id not $actual_account_id"
ok "Good. We're aiming at the right account"

s3base=$(config _.s3base)
shopt -s nullglob

# Install components
for fname in "${deployers[@]}"
do
	item="${fname#deploy_}"
	# Check if we should deploy this component.
	[ ${#components[@]} -ne 0 ] && ! contains "$item" "${components[@]}" && continue
	# Is this a skipped component.
	[ "$(config "$item")" = "" ] && info "🚫 Skipping $item" && continue

	info "🔵 Deploying $item"
	"$fname" || abort "$item deployment failed"
	[ "$dryrun" != "yes" ] && ok "$item deployed"
done
