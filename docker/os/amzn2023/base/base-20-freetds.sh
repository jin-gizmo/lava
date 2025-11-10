#!/bin/bash
# shellcheck disable=SC2154

# FreeTDS, ODBC guff

QUIET=--quiet

set -e

. utils.sh
. config.sh

require TDS_VER TDS_TLS


# ------------------------------------------------------------------------------
TMP=$(mktemp -d)
z=1
trap '/bin/rm -rf $TMP; exit $z' 0

info freetds - prereqs
dnf install unixODBC-devel -y $QUIET

info freetds - installing driver configuration
odbcinst -i -d -f resources/tds.driver.template

info freetds - package download
cd "$TMP"
wget --no-verbose "http://ftp.freetds.org/pub/freetds/stable/freetds-${TDS_VER}.tar.gz"
tar xf "freetds-${TDS_VER}.tar.gz"
cd "freetds-${TDS_VER}"

case "$TDS_TLS"
in
	gnutls)
		dnf install gnutls-devel -y $QUIET
		TDS_CONFIG_OPTIONS="$TDS_CONFIG_OPTIONS --with-gnutls" 
		;;
	openssl)

		dnf install openssl openssl-devel -y $QUIET
		TDS_CONFIG_OPTIONS="$TDS_CONFIG_OPTIONS --with-openssl=$(openssl version -d | cut -d'"' -f2)" 
		;;
	*)
		abort "$TDS_TLS: Unknown TDS TLS option"
		;;
esac

info freetds - configure
info "Configuring TDS build with options $TDS_CONFIG_OPTIONS"
# shellcheck disable=SC2086
./configure $TDS_CONFIG_OPTIONS

info freetds - build
make

info freetds - install
make install
ldconfig

tsql -C

z=0
