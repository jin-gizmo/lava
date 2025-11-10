#!/bin/bash

# Install MySQL CLI

QUIET=--quiet

set -e

. utils.sh
. config.sh

info Installing MySQL
rpm --import https://repo.mysql.com/RPM-GPG-KEY-mysql-2023
dnf install https://dev.mysql.com/get/mysql80-community-release-el9-5.noarch.rpm -y $QUIET
dnf install mysql-community-client -y $QUIET
