#!/bin/bash
# shellcheck disable=2034

# This file must be sourced -- not run in a subshell

# ------------------------------------------------------------------------------
TDS_VER=1.5.4

# TDS_TLS=gnutls
TDS_TLS=openssl
# Extra configure options (exclude TLS/SSL ones)
TDS_CONFIG_OPTIONS=

# ------------------------------------------------------------------------------
# https://ftp.gnu.org/pub/gnu/libiconv/libiconv-${ICONV_VER}.tar.gz
ICONV_VER=1.18

# ------------------------------------------------------------------------------
# This is the Australian mirror. We don't trust the mirrors for sig files which
# must come from ftp.gnu.org. Note the ftp.gnu.org is very slow.
GNU_MIRROR=mirrors.middlendian.com

# ------------------------------------------------------------------------------
# Basiclite is a lot smaller (less language files etc).
# ORACLE_TYPE=basic
ORACLE_TYPE=basiclite

# ------------------------------------------------------------------------------
PYTHON_VERSION=3.12

# ------------------------------------------------------------------------------
export DEBIAN_FRONTEND=noninteractive
