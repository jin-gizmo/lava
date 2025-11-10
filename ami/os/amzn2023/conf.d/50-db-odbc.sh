#!/bin/bash
# ex: sw=4 ts=4 et ai

# ------------------------------------------------------------------------------
# Install ODBC / Free TDS
# ------------------------------------------------------------------------------

TDS_VER=1.5.4

set -e

. lib/funcs.sh

arch=$(arch)
dnf install tar wget bzip2 unixODBC-devel gnutls-devel -y
wget http://ftp.freetds.org/pub/freetds/stable/freetds-${TDS_VER}.tar.bz2
info freetds - build
rpmbuild -tb --clean freetds-${TDS_VER}.tar.bz2

info freetds - install
rpmdir=/root/rpmbuild
(
	cd "${rpmdir}/RPMS/${arch}"
	rpm -i "freetds-${TDS_VER}-1.${arch}.rpm"
	rpm -i "freetds-unixodbc-${TDS_VER}-1.${arch}.rpm"
	rpm -i "freetds-devel-${TDS_VER}-1.${arch}.rpm"
	# libtool --finish /usr/lib64
)
/bin/rm -rf $rpmdir "freetds-${TDS_VER}.tar.bz2"

odbcinst -i -d -f resources/tds.driver.template
