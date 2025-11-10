#!/bin/bash

# Base build script for Amazon Linux 2023

QUIET=--quiet

set -e

. utils.sh
. config.sh

require PYTHON_VERSION

echo "--------------------------------------------------------------------------------"
# shellcheck disable=SC2154
info "Build target is $NAME $VERSION ($ARCH1 / $ARCH2)"
echo "--------------------------------------------------------------------------------"

# ------------------------------------------------------------------------------
# Install the base packages

# shellcheck disable=SC2154
PKGS=(
	bzip2
	dnf-utils
	hostname
	libpq-devel
	postgresql15
	"python${PYTHON_VERSION}"
	"python${PYTHON_VERSION}-devel"
	"python${PYTHON_VERSION}-pip"
	tar
	util-linux
	wget
)

# Add any required third party Python modules here. Don't include the ones
# lava itself uses. On amzn2023, don't include pip (installed via dnf).
PYMODULES=(
)

info Updating base packages
dnf update -y $QUIET

info Installing dev tools
dnf groupinstall "Development Tools" -y $QUIET

info Installing packages
dnf install "${PKGS[@]}" -y $QUIET

# Amazon Linux 2023 comes with Python 3.9 ffs.
for p in python pip pydoc
do
	ln -s "/usr/bin/${p}${PYTHON_VERSION}" "/usr/local/bin/${p}3"
done

installed_python=$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
[  "$installed_python" != "$PYTHON_VERSION" ] && \
	abort "Expected Python $PYTHON_VERSION - got $installed_python"
info "Python $PYTHON_VERSION installed and verified"

# ------------------------------------------------------------------------------
# Foundational Python modules.
# Here we are relying on /usr/local/bin being early in the path
# Pip is a bit special because of the dnf install earlier
# python3 -m pip install --no-cache-dir --force-reinstall --ignore-installed -U pip
if [ ${#PYMODULES[@]} -gt 0 ]
then
	info Installing core Python modules
	python3 -m pip install --no-cache-dir -U "${PYMODULES[@]}"
fi
