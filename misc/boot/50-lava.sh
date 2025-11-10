#!/bin/bash
# ex ft=bash

# ------------------------------------------------------------------------------
# Install and setup script for an Amazon Linux 2023 based lava worker.
#
# This assumes either a lava AMI or a SAK AMI base (deprecated).
#
# Usage: 50-lava.sh s3-source-area realm worker
#
# The s3-source-area is where we find the lava code bundle. It must have this
# layout:
#
#    s3-source-area/
#        _dist_/
#            pkg/
#                <OS_TYPE-1>/
#                    lava-<VERSION-1>.tar.bz2
#                    lava-<VERSION-2>.tar.bz2
#                    lava-<VERSION-3>-<OS_TYPE_1>-py<PYTHON-VERSION>-<ARCH>.tar.bz2
#                    ...
#                <OS_TYPE-2>/
#                    lava-<VERSION-1>.tar.bz2
#                    lava-<VERSION-2>.tar.bz2
#                    ...
#
# The <OS-TYPE..> values must match the lava notion of such things (e.g. amzn2,
# amzn2018 etc).
#
# ------------------------------------------------------------------------------
# Note that we have two different styles of filename for the code bundle.
# The old style is like this:
# 	lava-<VERSION-1>.tar.bz2
# The new style is like this:
# 	lava-<VERSION-3>-<OS-TYPE-1>-py<PYTHON-VERSION>-<ARCH>.tar.bz2
# 	lava-8.1.0-amzn2-py3.11-aarch64.tar.bz2
#
# The realms table entry can contain parameters under the "x-workers.<WORKER>"
# key that modify the behaviour of this script as follows. Note that a <WORKER>
# value of "_" in the realms table can provide defaults for all workers where
# a worker specific value is not provided.
#
# | ------- | ------ | ----------------------------------------- |
# | Key     | Type   | Description                               |
# | ------- | ------ | ----------------------------------------- |
# | version | String | Lava version to install (e.g. 5.1.0)      |
# | threads | Int    | Number of threads to run per daemon.      |
# | workers | String | A space separated list of workers to run. |
# | daemons | String | Number of daemons to run. Default is 1.   |
# | ------- | ------ | ----------------------------------------- |
#
# ------------------------------------------------------------------------------
#
# By default, the script will attempt to install the highest available version
# that matches the current O/S type, Python version and architecture. The old
# style naming didn't have this extra detail other than O/S type which could
# lead to compatibility issues if not careful.
#
# The package selection sequence is this:
#
# 	1.  If a version is specified in the realms table:
# 	    a.  Look for a package with the new package naming style (i.e. version,
# 	        OS, architecture and Python must match). If one is found, use that.
# 	    b.  Look for a package of the required version with the old naming
# 	        style. If one is found, use that.
# 	2.  If a version is not specified in the realms table:
# 	    a.  Find the latest matching version using the new package naming
# 	        style. If one is found, use that.
# 	    b.  Find the latest version using the old package name style. If one
# 	        is found, use that.
# 	3.  Otherwise, give up and abort.

# Where the symlinks to lava binaries go
LAVA_BIN=/usr/local/bin
LAVAPATH=$LAVA_BIN:/usr/bin

PROG=$(basename "$0")

# ******************************************************************************
# Functions
# ******************************************************************************

# ..............................................................................
function info {
	[ -t 2 ] && echo "INFO: $*" >&2
	logger -t "$PROG" -p local0.info "INFO: $*"
}

function error {
	[ -t 2 ] && echo "ERROR: $*" >&2
	logger -t "$PROG" -p local0.error "ERROR: $*"
}

# Usage: abort message
function abort {
	error "ABORT $*"
	exit 1
}

# ..............................................................................
# Get the OS type and major version ... eg. centos8, ubuntu18, darwin18 ...
function os_type {
	local ID
	local VERSION_ID

	if [ -f /etc/os-release ]
	then
		# shellcheck disable=SC1091
		. /etc/os-release
	else
		ID=$(uname -s | tr '[:upper:]' '[:lower:]')
		VERSION_ID=$(uname -r)
	fi

	[ "$ID" = "" ] && error "Cannot determine O/S type" && return 1
	[ "$VERSION_ID" = "" ] && error "Cannot determine O/S version" && return 1

	# Get major version
	VERSION_ID=$(expr "$VERSION_ID" : '\([^.]*\)')
	echo "${ID}${VERSION_ID}"
}

# ..............................................................................
# Print lines from stdin that match the specified glob pattern.
function glob {
    python3 -c "
import sys
from fnmatch import fnmatchcase
for line in sys.stdin:
    line = line.rstrip('\n')
    if fnmatchcase(line, '$1'):
        print(line)
    "
}

# ..............................................................................
function get_realm_info {
	aws dynamodb get-item --table-name lava.realms --key "{\"realm\": {\"S\": \"$1\"}}"
}

# ..............................................................................
# Work out if we have lava or SAK AMI.
function get_ami_type {
	# Lava AMI instances have an explicit marker.
	if [ -f /usr/local/etc/ami-info ]
	then
		# shellcheck disable=SC1091
		.  /usr/local/etc/ami-info
		echo "$AMI_TYPE"
		return 0
	fi
	# SAK AMI instances don't have an explicit marker. Look for signs.
	[ -f /usr/local/etc/rc.d/00_shell.sh ] && echo SAK && return 0
	echo unknown
}

# ..............................................................................
# Extract an realm value from the wacky DynamoDB JSON. Single arg is the item
# path using dot notation.
function get_realm_item {
	python3 -c "
import json, sys;
with open('$TMPDIR/realm.json') as fp:
    r = json.load(fp)['Item']
    for k in '$1'.split('.'):
        try:
            r = list(r[k].values())[0]
        except KeyError:
            r = ''
            break
    print(r)
"
}

# ..............................................................................
# Look for an x-worker config item from the realms table entry for the realm.
# Usage: get_worker_item worker item
function get_worker_item {
	local item="$2"

	val=$(get_realm_item "x-workers.$1.$item")
	[ "$val" != "" ] && echo "$val" && return 0

	get_realm_item "x-workers._.$item"
}

# ..............................................................................
# Look for an "env" (environment) block in x-worker config item from the realms
# table entry for the realm. Output is a bunch of environment setting commands.
# Usage: get_worker_env worker
function get_worker_env {
	python3 -c "
import json, sys, re;
with open('$TMPDIR/realm.json') as fp:
    r = json.load(fp)['Item']

try:
    env = r['x-workers']['M']['$1']['M']['env']['M']
except KeyError:
    try:
        env = r['x-workers']['M']['_']['M']['env']['M']
    except KeyError:
        exit(0)
if not env:
    exit(0)
for k,v in env.items():
    if not re.match(r'^\w+$', k):
        continue
    val = str(list(v.values())[0])
    if '\'' in val:
        continue
    print(f'export {k}=\'{val}\'')

"
}

# ..............................................................................
# Find the latest version of something in S3 based on a version number component
# in the name. Returns the basename of the object if found.
# Usage: s3_latest_version s3://bucket/prefix glob
function s3_latest_version {
	aws s3 ls "$1" | awk '{print $4}' | glob "${2-*}" |  sort -r --version-sort | head -1
}

# ..............................................................................
# Check if an S3 object exists.
# Usage: s3_exists bucket key
function s3_exists {
	aws s3api head-object --bucket "$1" --key "$2" > /dev/null 2>&1
}

# ..............................................................................
# Compare two version numbers (dot separated integers).
# Usage: version_gt v1 v2
# Return status is 0 if $1 > $2, otherwise 1.
#
# Behaves like >= when second arg is major.minor only
function version_gt {
        high=$( (echo "$1"; echo "$2") | sort -r --version-sort | head -1)
        [ "$1" != "$2" -a "$high" = "$1" ]
}

# ..............................................................................
# Try to get machine architecture in some cannonical way. Don't talk to me about
# /usr/bin/arch (uname -m) ... all over the place and no consistency.

case $(uname -m)
in
	arm64 | aarch64)	ARCH1=aarch64; ARCH2=arm64 ;;
	x64 | x86_64)		ARCH1=x86_64 ; ARCH2=x64 ;;
	*) 		abort "$(uname -m): Unknown architecture - abort" ;;
esac

os=$(os_type)
[ $? -ne 0 ] && exit 1

arch=$(arch)
[ $? -ne 0 ] && exit 1

py_ver=$(python3 -c 'from sys import version_info as v; print(f"{v.major}.{v.minor}")')


# ******************************************************************************
# Real work starts here
# ******************************************************************************

info Starting

ami=$(get_ami_type)
case "$ami"
in
	lava | SAK)	info "AMI type appears to be $ami";;
	*)		abort "AMI type is $ami -- cannot handle that"
esac

info "Platform appears to be $os on $ARCH1 ($ARCH2)"

# Make sure SSM agent is running
systemctl enable amazon-ssm-agent
systemctl start amazon-ssm-agent
systemctl status amazon-ssm-agent

[ $# -ne 3 ] && abort "Usage: $PROG s3-source-area realm worker"

s3source="$1"
realm="$2"
worker="$3"

[[ ! "$s3source" =~ ^s3://([^/]+)/(.+) ]] && abort "Malformed s3-source-area: $s3source"
dist_bkt="${BASH_REMATCH[1]}"
dist_pfx="${BASH_REMATCH[2]}"


TMPDIR=/tmp/lava.$$
z=1
trap '/bin/rm -rf $TMPDIR; exit $z' 0
mkdir -p $TMPDIR


# ******************************************************************************
# Install lava.
# ******************************************************************************

info Installing lava

get_realm_info "$realm" > "$TMPDIR/realm.json"
[ ! -s "$TMPDIR/realm.json" ] && abort "$realm: No such realm"

pkg_pfx="$dist_pfx/_dist_/pkg/$os"
lava_pkg=

# ..............................................................................
# Work out which lava version to install

# See if realms table tells us what version to install
lava_version=$(get_worker_item "$worker" version)

if [ "$lava_version" != "" ]
then
	# Look for the specified version
	info "Looking for lava v${lava_version} in $dist_bkt/$pkg_pfx"
	
	# Look for the new naming format first, then the old format
	for p in "lava-${lava_version}-${os}-py${py_ver}-${arch}.tar.bz2" "lava-${lava_version}.tar.bz2"
	do
		if s3_exists "$dist_bkt" "$pkg_pfx/$p"
		then
			lava_pkg="$p"
			break
		fi
	done
	[ "$lava_pkg" = "" ] && abort "Cannot find lava v${lava_version} install package in S3"
else
	# Look for the latest available version using new and old package names
	for pattern in "lava-*-${os}-py${py_ver}-${arch}.tar.bz2" "lava-*.tar.bz2"
	do
		p=$(s3_latest_version "$dist_bkt/$pkg_pfx/lava-" "$pattern")
		if [ "$p" != "" ]
		then
			lava_pkg="$p"
			break
		fi
	done
	[ "$lava_pkg" = "" ] && abort "Cannot find lava install package in S3"
	lava_version=$(echo "$lava_pkg" | sed -e 's/lava-\([1-9][0-9]*\.[0-9][0-9]*\.[0-9][0-9]*\).*/\1/')
	info "Found lava version $lava_version"
fi


# ..............................................................................

# Download the install package
info "Downloading s3://$dist_bkt/$pkg_pfx/$lava_pkg"
aws s3 cp --no-progress "s3://$dist_bkt/$pkg_pfx/$lava_pkg" "$TMPDIR" || abort Cannot get install package from S3

# Extract the installer
tar -xf "$TMPDIR/$lava_pkg" -C "$TMPDIR" install.sh || abort Cannot extract installer from install package
chmod 700 $TMPDIR/install.sh

# Run the installer.
# v8 changed the way the installer works a bit (slightly different semantics on -d option)
# Note that version_gt behaves like >= when second arg is major.minor only
if version_gt "$lava_version" 8.0
then
	info "Running lava installer (v8+)"
	lava_base=/opt/lava
else
	info "Running lava installer (v7)"
	lava_base=/usr/local
fi
$TMPDIR/install.sh -c -d "$lava_base" "$TMPDIR/$lava_pkg" || abort Lava install failed


export PATH="$LAVA_BIN:$PATH"
installed_lava_version=$(lava-version)
[ $? -ne 0 -o "$installed_lava_version" == "" ] && abort Cannot determine installed lava version
info "Installed lava v${installed_lava_version}"

# Lava v7.1.0 introduced "--log-json" option.
# Note that version_gt behaves like >= when second arg is major.minor only
version_gt "$installed_lava_version" 7.1 && worker_args="--log-json"

# ..............................................................................
# Create the lava group

if ! getent group lava > /dev/null
then
	info No lava group - creating
	groupadd lava
fi

# Clean out the old tmp area and create a new one
/bin/rm -rf /tmp/lava
mkdir -p "/tmp/lava/$realm"
chgrp -R lava /tmp/lava
chmod -R 1770 /tmp/lava

workers=$(get_worker_item "$worker" workers)
[ "$workers" == "" ] && workers="$worker"

# Create user accounts and start a lava daemon for each worker
for w in $workers
do
	user=lava-$w

	# Create dedicated system account for each worker

	if ! getent passwd "$user" > /dev/null
	then
		info "No $user account - creating"
		useradd "$user" -g lava --system --create-home --no-user-group \
			--comment "Lava Worker $w" --shell /bin/false
		usermod --lock "$user"
	fi

	# Add each user to the docker group
	usermod -aG docker "$user"

	# Get any argument overrides
	extra_args="$worker_args"
	threads=$(get_worker_item "$w" threads)
	if [ "$threads" != "" ]
	then
		[[ "$threads" == +([0-9]) ]] || abort "$threads: Bad thread count for worker $w"
		extra_args="$extra_args --threads $threads"
	fi

	# How many worker daemons do we run.
	daemons=$(get_worker_item "$w" daemons)
	if [ "$daemons" != "" ]
	then
		[[ "$daemons" == +([0-9]) ]] || abort "$daemons: Bad daemon count for worker $w"
	else
		daemons=1
	fi


	# Start the lava worker

	info "Starting lava worker for realm=$realm worker=$w"
	(
		eval cd ~"$user"

		# Build a little script to start the worker.
		cat > lava.start <<-!
			#!/bin/bash

			export PATH="$LAVAPATH"
			$(get_worker_env "$w")

			lava-worker \
				--realm "$realm" \
				--worker "$w" \
				--jump-start \
				--daemon \
				--heartbeat 60 \
				--tag "lava-$realm-$w" \
				--log @local0 \
				--level info \
				$extra_args

		!
		chown "$user" lava.start
		chgrp lava lava.start
		chmod 750 lava.start 

		n=1
		while [ "$n" -le "$daemons" ]
		do
			info "Lava worker $w: Starting daemon $n of $daemons"
			sudo -Hnu "$user" ./lava.start
			[ $? -ne 0 ] && abort "Lava worker $w: Daemon $n of $daemons failed"
			n=$((n+1))
		done
	)
done

# ..............................................................................
z=0
info Done
