#!/bin/bash
# ex: sw=4 ts=4 et ai

# ------------------------------------------------------------------------------
# Install OpenSSL from source to ensure a predictable version. Must be done
# before Python build.
# ------------------------------------------------------------------------------

# OPENSSL_VERSION=3.2.1
OPENSSL_VERSION=3.5.0
OPENSSL_PREFIX=/usr/local

set -e

. lib/funcs.sh

yum install perl-IPC-Cmd perl-core -y

mkdir /tmp/openssl.$$
z=1
trap '/bin/rm -r /tmp/openssl.$$; exit $z' 0

cd /tmp/openssl.$$
wget "https://www.openssl.org/source/openssl-${OPENSSL_VERSION}.tar.gz"

tar xf openssl-${OPENSSL_VERSION}.tar.gz
cd openssl-${OPENSSL_VERSION}

./config --openssldir="$OPENSSL_PREFIX" --prefix="$OPENSSL_PREFIX"
make
# make test
make install

# Need to work out where our SSL libraries went. This is architecture specific.
libdir=
for d in lib lib64
do
	[ ! -f "$OPENSSL_PREFIX/$d/libssl.so" ] && continue
	info "Found SSL libs in $d"
	libdir="$d"
	echo "$OPENSSL_PREFIX/$d" > /etc/ld.so.conf.d/openssl.conf
	ldconfig
	break
done

[ "$libdir" == "" ] && abort "Could not find SSL libraries"

$OPENSSL_PREFIX/bin/openssl version
z=0
