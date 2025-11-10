#!/bin/bash
# shellcheck disable=SC2154

# FreeTDS, ODBC guff

QUIET=--quiet

set -e

. utils.sh
. config.sh

require TDS_VER TDS_TLS ICONV_VER GNU_MIRROR

# ------------------------------------------------------------------------------
TMP=$(mktemp -d)
z=1
trap '/bin/rm -rf $TMP; exit $z' 0

info freetds - prereqs
dnf install 'dnf-command(config-manager)' -y $QUIET
dnf config-manager --set-enabled crb
dnf install unixODBC-devel -y $QUIET

info freetds - installing driver configuration
odbcinst -i -d -f resources/tds.driver.template

# ------------------------------------------------------------------------------
info libiconv - package download
mkdir -p "$TMP/iconv"
cd "$TMP/iconv"
wget --no-verbose "https://${GNU_MIRROR}/gnu/libiconv/libiconv-${ICONV_VER}.tar.gz"
# We don't trust the mirror for sig files.
wget --no-verbose "https://ftp.gnu.org/pub/gnu/libiconv/libiconv-${ICONV_VER}.tar.gz.sig"
# Check the package signature
wget --no-verbose https://ftp.gnu.org/gnu/gnu-keyring.gpg
gpgv --keyring ./gnu-keyring.gpg "libiconv-${ICONV_VER}.tar.gz.sig" "libiconv-${ICONV_VER}.tar.gz" \
	|| abort "Bad signature on libiconv-${ICONV_VER}.tar.gz.sig"

tar xf "libiconv-${ICONV_VER}.tar.gz"
cd "libiconv-${ICONV_VER}"
info libiconv - configure
./configure
info libiconv - build
make
info libiconv - install
make install
ldconfig

# ------------------------------------------------------------------------------
info freetds - package download
mkdir -p "$TMP/freetds"
cd "$TMP/freetds"
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
