#!/bin/bash

# Base build script for Ubuntu

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

PKGS=(
	apt-utils
	build-essential
	curl
	file
	libpq-dev
	libtool
	pkg-config
	util-linux
	wget
	zip
	# In Ubuntu 2024 the system version of Python is 3.12.
	python3
	python3-dev
	python3-pip
	# ODBC guff
	# tdsodbc
	# freetds-dev
	# freetds-bin
	# unixodbc
	# unixodbc-dev
	# odbcinst
)

info Updating base packages
apt-get update
apt-get upgrade -y

info Installing packages
apt-get install "${PKGS[@]}" -y $QUIET

# Don't need this for Ubuntu 2024 as system version is Python 3.12
# for p in python pip pydoc
# do
# 	ln -s "/usr/bin/${p}${PYTHON_VERSION}" "/usr/local/bin/${p}3"
# done

# Make sure we got what the Python version expected
installed_python=$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
# shellcheck disable=SC2154
[  "$installed_python" != "$PYTHON_VERSION" ] && \
	abort "Expected Python $PYTHON_VERSION - got $installed_python"
info "Python $PYTHON_VERSION installed and verified"

