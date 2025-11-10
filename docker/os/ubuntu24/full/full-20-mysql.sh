#!/bin/bash

# Install MySQL CLI

QUIET=--quiet

set -e

. utils.sh
. config.sh

info Installing MySQL
wget -q -O - https://repo.mysql.com/RPM-GPG-KEY-mysql-2023 | apt-key add -
apt-get install mysql-client -y $QUIET
