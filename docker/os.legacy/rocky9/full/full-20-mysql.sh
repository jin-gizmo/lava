#!/bin/bash

# Install MySQL CLI
# We rely on the Rocky repos now


QUIET=--quiet

set -e

. utils.sh
. config.sh

# . .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .

# dnf install ${MYSQL_REPO}/mysql-community-common-${MYSQL_VER}.${ARCH1}.rpm -y $QUIET
# dnf install ${MYSQL_REPO}/mysql-community-client-plugins-${MYSQL_VER}.${ARCH1}.rpm -y $QUIET
# dnf install ${MYSQL_REPO}/mysql-community-libs-${MYSQL_VER}.${ARCH1}.rpm -y $QUIET
# dnf install ${MYSQL_REPO}/mysql-community-client-${MYSQL_VER}.${ARCH1}.rpm -y $QUIET

dnf config-manager --set-enabled crb
dnf install mysql mysql-devel -y $QUIET
dnf config-manager --set-disabled crb
