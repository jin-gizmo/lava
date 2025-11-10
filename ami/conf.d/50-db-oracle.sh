#!/bin/bash
# shellcheck disable=SC2154
# ex: sw=4 ts=4 et ai

# ------------------------------------------------------------------------------
# Install the Oracle client.
# ------------------------------------------------------------------------------

. lib/funcs.sh

require S3BUCKET S3PREFIX

ORACLE_TYPE=basiclite

# S3PREFIX should end with /
[[ "$S3PREFIX" == */ ]] || S3PREFIX="${S3PREFIX}/"

ora_s3_loc="s3://$S3BUCKET/${S3PREFIX}oracle"

arch2=$(arch 2)

oracle_pkgs=(
    "instantclient-${ORACLE_TYPE}-linux-${arch2}.zip"
    "instantclient-sqlplus-linux-${arch2}.zip"
)


# Prerequisites
yum install libaio -y

shopt -s nullglob

echo "Installing Oracle Instant Client"

TMPDIR=$(mktemp -d)
z=1
trap '/bin/rm -rf $TMPDIR; exit $z' 0

# Get Oracle zips from S3
for ora in "${oracle_pkgs[@]}"
do
    aws s3 cp --no-progress "$ora_s3_loc/$ora" "$TMPDIR" || \
        abort "Cannot download Oracle $ora from $ora_s3_loc"
    unzip -od /opt/oracle "$TMPDIR/$ora"
done

oracle_dir=$(echo /opt/oracle/instantclient*)
[ "$oracle_dir" == "" ] && abort "Cannot find Oracle Instant Client installation"

echo "$oracle_dir" > /etc/ld.so.conf.d/oracle-instantclient.conf
ldconfig
[ -e /usr/bin/sqlplus ] && /bin/rm -f /usr/bin/sqlplus
ln -s "$oracle_dir/sqlplus" /usr/bin

# Confirm it works
version=$(echo /opt/oracle/instantclient* | sed 's/.*instantclient_\(.*\)/\1/' | tr '_' '.')
[ "$version" == "" ] && abort "Oracle Instant Client install failed"

info "Oracle version $version installed"
sqlplus -V

z=0
