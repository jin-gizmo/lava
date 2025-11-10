#!/bin/bash

# ------------------------------------------------------------------------------
# Generic boot script for an EC2 (amazon linux) lava worker.
#
# Usage: root.boot.sh s3-source-area realm worker
#
# The s3-source-area is where we find the lava code bundle and its installer.
# ------------------------------------------------------------------------------

PROG=$(basename "$0")

# ------------------------------------------------------------------------------
function info {
	[ -t 2 ] && echo "INFO: $*" >&2
	logger -t "$PROG" -p local0.info "INFO: $*"
}

function warning {
	[ -t 2 ] && echo "WARNING: $*" >&2
	logger -t "$PROG" -p local0.error "WARNING: $*"
}

function error {
	[ -t 2 ] && echo "ERROR: $*" >&2
	logger -t "$PROG" -p local0.error "ERROR: $*"
}

# Usage: abort message
function abort {
	[ -t 2 ] && echo "$PROG: ABORT - $*" >&2
	error "ABORT $*"
	exit 1
}

# ------------------------------------------------------------------------------

[ $# -ne 3 ] && abort "Usage: $PROG s3-source-area realm worker"

s3source="$1"
[[ ! "$s3source" =~ ^s3:// ]] && abort "s3-source-area must start with s3://"

realm="$2"
worker="$3"

info Starting

# ------------------------------------------------------------------------------
TMPDIR=/tmp/boot.$$
z=1
trap '/bin/rm -rf $TMPDIR; exit $z' 0

# ------------------------------------------------------------------------------
# Check for boot scripts to run. This avoids the need to build environment
# specific customisations in the main boot script. Boot scripts must be located
# in $s3source/_boot_/ and will be run in lexicographic order. Recursion is not
# supported. Scripts that exit with status 1 will abort the main boot script.
# Any other exit status will allow the main boot script to continue.

mkdir -p $TMPDIR
cd $TMPDIR || error "Cannot cd to $TMPDIR/boot"

info "Checking $s3source/_boot_/ for boot scripts"
aws s3 sync "$s3source/_boot_/" .

shopt -s nullglob
for f in *
do
	[[ "$f" == README* ]] && continue
	[ ! -f "$f" ] && warning "Skipping non-file $f in boot scripts" && continue
	chmod 700 "$f"

	# Run the boot script. It must accept same args as this script.
	info "Running boot script $f"
	"./$f" "$s3source" "$realm" "$worker"

	case $? in
	0)	info "Boot script $f : OK";;
	1)	abort "Boot script $f failed";;
	*)	error "Boot script $f failed - continue";;
	esac
done

# ------------------------------------------------------------------------------
z=0
info Done
