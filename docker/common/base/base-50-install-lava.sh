#!/bin/bash
# shellcheck disable=SC2154

# ------------------------------------------------------------------------------
# Install Lava
#
# This relies on finding lava.tar.bz2 containing all the lava source in the
# current directory. We also assume the current directory is read-only.

. utils.sh
. config.sh

require LAVA_VERSION LAVA_BASE

LAVA_BIN=/usr/local/bin
LAVA_PYLIB="$LAVA_BASE/pylib"
LAVA_PKG="lava-${LAVA_VERSION}.tar.bz2"

set -e

TMP=$(mktemp -d)
CODE_DIR=$(pwd)

z=1
trap '/bin/rm -rf $TMP; exit $z' 0

# Need to switch to a writeable directory.
cd "$TMP"
ln -s "$CODE_DIR/$LAVA_PKG" .

tar --no-same-owner -xf "$LAVA_PKG" requirements.txt requirements-extra.txt install.sh

# python3 -m pip --no-cache-dir install 'pip>=20.3' setuptools wheel --upgrade ; \

./install.sh -c -b "$LAVA_BIN" -d "$LAVA_BASE" "$LAVA_PKG"

mkdir -p "$LAVA_PYLIB"
for f in requirements.txt requirements-extra.txt
do
	python3 -m pip -q install --target "$LAVA_PYLIB" --upgrade -r "$f"
done

info "Lava version $($LAVA_BIN/lava-version) installed"

z=0
