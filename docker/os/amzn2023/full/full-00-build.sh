#!/bin/bash

# Full build script for Amazon Linux. Must be built on a lava base build for
# Amazon Linux.

QUIET=--quiet

set -e

. utils.sh
. config.sh

echo "--------------------------------------------------------------------------------"
# shellcheck disable=SC2154
info "Build target is $NAME $VERSION ($ARCH1 / $ARCH2)"
echo "--------------------------------------------------------------------------------"

dnf update -y $QUIET
dnf install libaio -y $QUIET
