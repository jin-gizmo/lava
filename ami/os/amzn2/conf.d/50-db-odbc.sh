#!/bin/bash
# ex: sw=4 ts=4 et ai

# ------------------------------------------------------------------------------
# Install ODBC / Free TDS
# ------------------------------------------------------------------------------

set -e

. lib/funcs.sh

yum install unixODBC-devel -y
amazon-linux-extras install epel -y
yum install freetds freetds-devel -y
yum install unixODBC-devel -y
odbcinst -i -d -f resources/tds.driver.template


# Disable EPEL so yum updates won't go back there later on as it could be
# blocked by VPC network access controls.
amazon-linux-extras disable epel
yum-config-manager --disable epel
