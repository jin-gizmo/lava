#!/bin/bash

# Full build script for Ubuntu. Must be built on a lava base build for Ubuntu.

QUIET=--quiet

set -e

. utils.sh
. config.sh

echo "--------------------------------------------------------------------------------"
# shellcheck disable=SC2154
info "Build target is $NAME $VERSION ($ARCH1 / $ARCH2)"
echo "--------------------------------------------------------------------------------"

PKGS=(
	git
	libaio1t64
	wget
)

apt-get update $QUIET
apt-get upgrade -y $QUIET
apt-get install "${PKGS[@]}" -y $QUIET
ln -s "/usr/lib/${ARCH1}-linux-gnu/libaio.so.1t64" /usr/lib/libaio.so.1
