#!/bin/bash
# ex ft=bash

# ------------------------------------------------------------------------------
# Install extra pre-requisites.
# This is a hack for non-lava AMIs (i.e. SAK). Lava AMI doesn't need this.
#
# Usage: 40-extras.sh s3-source-area [...]
#
# The s3-source-area is where we find the lava code bundle and extra bits needed
# here. It must have this layout:
#
#    s3-source-area/
#        _dist_/
#            other/
#                ... Oracle and any other 3rd party stuff
#            rpm/
#                ... RPMs needing to be installed
#
#
# ------------------------------------------------------------------------------


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
	[ -t 2 ] && echo "$PROG: ABORT - $*" >&2
	error "ABORT $*"
	exit 1
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
# Try to get machine architecture in some cannonical way. Don't talk to me about
# /usr/bin/arch (uname -m) ... all over the place and no consistency.

case $(uname -m)
in
	arm64 | aarch64)	ARCH1=aarch64; ARCH2=arm64 ;;
	x64 | x86_64)		ARCH1=x86_64 ; ARCH2=x64 ;;
	*) 		abort "$(uname -m): Unknown architecture - abort" ;;
esac


# ------------------------------------------------------------------------------
# Real work starts here
# ------------------------------------------------------------------------------

info Starting

ami=$(get_ami_type)
case "$ami"
in
	lava)	info "Extras install not required on lava AMI"; exit 0;;
	SAK)	info "AMI type appears to be $ami";;
	*)	abort "AMI type is $ami -- cannot handle that"
esac

info "Platform appears to be $ARCH1 ($ARCH2)"

s3source="$1"
[[ ! "$s3source" =~ ^s3://([^/]+)/(.+) ]] && abort "Malformed s3-source-area: $s3source"
dist="$s3source/_dist_"


TMPDIR=/tmp/lava-extras.$$
z=1
trap '/bin/rm -rf $TMPDIR; exit $z' 0
mkdir -p $TMPDIR


# Make sure docker is installed.
docker info >/dev/null
if [ $? -eq 127 ]
then
	info Installing docker
	yum install docker -y
	service docker restart
fi

# Grab any extra RPMs that aren't in the AWS repos as we don't want to depend on
# public repos at boot time.
aws s3 cp --no-progress "$dist/rpm/" "$TMPDIR" --exclude "*" --include "*.${ARCH1}.rpm" --rec || \
	abort "Cannot download RPMs"
shopt -s nullglob
set --  $TMPDIR/*
if [ $# -gt 0 ]
then
	info "Installing extra RPMs"
	yum install -y $TMPDIR/*.rpm
fi

# ODBC -- requires freetds to be present.
info Installing ODBC components
yum install unixODBC-devel -y
odbcinst -i -d -r <<-!
	[FreeTDS]
	Description	= Free TDS ODBC driver
	Driver		= /usr/lib64/libtdsodbc.so.0
!
info ODBC install complete

# ..............................................................................
z=0
info Done
