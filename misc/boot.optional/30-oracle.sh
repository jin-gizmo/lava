#!/bin/bash
# ex ft=bash

# ------------------------------------------------------------------------------
# WARNING: This is based on the same code as the lava AMI build but it is
#          UNTESTED in this script.
#
# ------------------------------------------------------------------------------
# Install Oracle client. The ZIP packages must be in the lava code area in S3
# (s3source).
#
# This is required for SAK AMI. The lava AMI comes with a version of Oracle
# preinstalled so this is not
# required.
#
# Usage: 30-oracle.sh s3-source-area [...]
#
# The s3-source-area is where we find the lava code bundle and extra bits such
# as the Oracle binaries needed here. It must have this layout:
#
#    s3-source-area/
#        _dist_/
#            other/
#                instantclient-basiclite-linux-x64.zip
#                instantclient-sqlplus-linux-x64.zip
# ------------------------------------------------------------------------------

ORACLE_TYPE=basiclite
PROG=$(basename "$0")

oracle_pkgs=(
    "instantclient-${ORACLE_TYPE}-linux-${arch2}.zip"
    "instantclient-sqlplus-linux-${arch2}.zip"
)

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
# Try to get machine architecture in some cannonical way. Don't talk to me about
# /usr/bin/arch (uname -m) ... all over the place and no consistency.

case $(uname -m)
in
	arm64 | aarch64)
		ARCH1=aarch64; ARCH2=arm64 ;;
	x64 | x86_64)
		ARCH1=x86_64 ; ARCH2=x64 ;;
	*)
		abort "$(uname -m): Unknown architecture - abort" ;;
esac

# ------------------------------------------------------------------------------
# Real work starts here
# ------------------------------------------------------------------------------

info Starting

ami=$(get_ami_type)
case "$ami"
in
	lava | SAK)	info "AMI type appears to be $ami";;
	*)		abort "AMI type is $ami -- cannot handle that"
esac

info "Platform appears to be $ARCH1 ($ARCH2)"

s3source="$1"
[[ ! "$s3source" =~ ^s3://([^/]+)/(.+) ]] && abort "Malformed s3-source-area: $s3source"
ora_s3_loc="$s3source/_dist_/other"


# ------------------------------------------------------------------------------

info "Checking if Oracle client is already installed"
sqlplus -V && info "Oracle client already installed" && exit 0


# ------------------------------------------------------------------------------
info "Oracle client is not installed -- will install"
TMPDIR=$(mktemp -d)
z=1
trap '/bin/rm -rf $TMPDIR; exit $z' 0

# Prerequisites
yum install libaio -y

# Get Oracle zips from S3
for ora in "${oracle_pkgs[@]}"
do
    aws s3 cp --no-progress "$ora_s3_loc/$ora" "$TMPDIR" || \
        abort "Cannot download Oracle $ora from $ora_s3_loc"
    unzip -od /opt/oracle "$TMPDIR/$ora"
done


oracle_dir=$(echo /opt/oracle/instantclient*)
[ "$oracle_dir" == "" ] && abort "Cannot find Oracle installation"

echo "$oracle_dir" > /etc/ld.so.conf.d/oracle-instantclient.conf
ldconfig
[ -e /usr/bin/sqlplus ] && /bin/rm -f /usr/bin/sqlplus
ln -s "$oracle_dir/sqlplus" /usr/bin

# Confirm it works
version=$(echo /opt/oracle/instantclient* | sed 's/.*instantclient_\(.*\)/\1/' | tr '_' '.')
[ "$version" == "" ] && abort "Oracle install failed"

info "Oracle version $version installed"
sqlplus -V

z=0
info Done
