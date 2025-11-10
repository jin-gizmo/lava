#!/bin/bash
# shellcheck disable=SC2154

# Install Oracle Instant Client from local zips in the "packages" directory.
#
# As of lava v8.1, versioned Oracle install zips have names like this:
# 	instantclient-basiclite-linux-arm64-23.8.zip
# 	instantclient-sqlplus-linux-arm64-23.8.zip

set -e

. utils.sh
. config.sh

# ORACLE_TYPE is "basic" or "basiclite".
require ORACLE_TYPE

info Installing Oracle Instant Client

unzip -od /opt/oracle "packages/instantclient-${ORACLE_TYPE}-linux-${ARCH2}.zip"
unzip -od /opt/oracle "packages/instantclient-sqlplus-linux-${ARCH2}.zip"

oracle_dir=$(echo /opt/oracle/instantclient*)

# Fix paths for Oracle
# echo "export PATH=$PATH:$oracle_dir" > /etc/profile.d/oraclepath.sh
# echo "export PATH=$PATH:$oracle_dir" >> /etc/bash.bashrc
echo "$oracle_dir" > /etc/ld.so.conf.d/oracle-instantclient.conf
ldconfig

ln -s "$oracle_dir/sqlplus" /usr/bin

version=$(echo /opt/oracle/instantclient* | sed 's/.*instantclient_\(.*\)/\1/' | tr '_' '.')
info "Oracle Instant Client version $version installed"

sqlplus -V
