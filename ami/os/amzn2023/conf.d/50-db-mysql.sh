#!/bin/bash
# ex: sw=4 ts=4 et ai

# ------------------------------------------------------------------------------
# Install the mysql client.
# AWS repos are sooo old. Don't use.
# ------------------------------------------------------------------------------

set -e

. lib/funcs.sh

MYSQL_VER=9-5
TMPDIR=$(mktemp -d)
z=1
trap '/bin/rm -rf $TMPDIR; exit $z' 0

cd "$TMPDIR"

rpm --import https://repo.mysql.com/RPM-GPG-KEY-mysql-2023
wget "https://dev.mysql.com/get/mysql80-community-release-el${MYSQL_VER}.noarch.rpm"
dnf install "mysql80-community-release-el${MYSQL_VER}.noarch.rpm" -y
/bin/rm -f "mysql80-community-release-el${MYSQL_VER}.noarch.rpm"
dnf install mysql-community-client -y

# We now have a bunch of mysql related repos active. We don't want to leave it
# that way because we don't want lava instances that may be locked down in a
# VPC trying to reach them later for updates.

for repo in $(dnf repolist | sed -ne '/^mysql/s?[ /].*??p')
do
    echo "Disabling repo: $repo"
    dnf config-manager --disable "$repo" > /dev/null
done

z=0
