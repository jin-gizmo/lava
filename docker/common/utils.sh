#!/bin/bash
# shellcheck disable=SC2034

# This file must be sourced -- not run in a subshell

prog=$(basename "$0")

# ------------------------------------------------------------------------------
# Get O/S info
source /etc/os-release

# ------------------------------------------------------------------------------
# Get architecture. There is no uniform standard for this so we have to set a
# couple of variants.

case $(uname -m)
in
	arm64 | aarch64)
		ARCH1=aarch64
		ARCH2=arm64
		;;
	x64 | x86_64)
		ARCH1=x86_64
		ARCH2=x64
		;;
	*)
		echo "$(uname -m): Unknown architecture - abort" >&2
		exit 1
		;;
esac

# ------------------------------------------------------------------------------
# Find the latest version of something based on a version number component
# in the name. Returns the basename of the object if found.
# Usage: latest_version prefix [regex]
function latest_version {
	# shellcheck disable=SC2010
	ls "$1"* | grep "${2-.}" | sort -r --version-sort | head -1
}


# ------------------------------------------------------------------------------
function info {
	echo "[34m${prog}: ${*}[0m"
}

function abort {
	echo "[31m${prog}: ABORT - ${*}[0m"
}


# ------------------------------------------------------------------------------
# Check that specified vars are set
function require {
	for i
	do
		[ "${!i}" = "" ] && abort "$i must be set"
	done
	return 0
}

