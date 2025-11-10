#!/bin/bash
# ex: sw=4 ts=4 et ai
#

# ------------------------------------------------------------------------------
# Common re-usable functions.
#
# This file needs to be sourced, not executed.
# ------------------------------------------------------------------------------


PROG=${PROG:-$(basename "$0")}


# . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . .
function info {
    echo "[34m$PROG: INFO: $*[0m" >&2
}

function warning {
    echo "[35m$PROG: WARNING: $*[0m" >&2
}

function abort {
    echo "[31m$PROG: ABORT: $*[0m" >&2
    exit 1
}


# . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . .
# Check that specified vars are set
function require {
    for i
    do
        [ "${!i}" = "" ] && abort "$i must be set"
    done
}


# . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . .
# Print lines from stdin that match the specified glob pattern.
function glob {
    python3 -c "
import sys
from fnmatch import fnmatchcase
for line in sys.stdin:
    line = line.rstrip('\n')
    if fnmatchcase(line, '$1'):
        print(line)
    "
}


# . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . .
# Find the latest version of something based on a version number component
# in the name.
# Usage: latest_version file ...
function latest_version {
	# shellcheck disable=SC2012
	ls "$@" | sort -r --version-sort | head -1
}


# . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . .
# Find the latest version of something in S3 based on a version number component
# in the name. Returns the basename of the object if found.
# Usage: s3_latest_version s3://bucket/prefix [glob]
function s3_latest_version {
	aws s3 ls "$1" | awk '{print $4}' | glob "${2-*}" |  sort -r --version-sort | head -1
}


# . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . .
# Try to get machine architecture in some cannonical way. Don't talk to me about
# /usr/bin/arch (uname -m) ... all over the place and no consistency.
# 
# Usage: arch [1|2|3]
# 
# If the argument is 1, the longer version is returned. If it's 2, the shorter
# version is returned. If it's 3, some other weird variation is returned.
function arch {
	local -a a
	local -i n=${1:-1}

	[ "$n" -lt 1 -o "$n" -gt 3 ] && abort "Bad arch selector: $n"

	case $(uname -m)
	in
	    arm64 | aarch64)    a=(- aarch64 arm64 arm64) ;;
	    x64 | x86_64)       a=(- x86_64 x64 amd64) ;;
	    *)                  abort "$(uname -m): Unknown architecture" ;;
	esac

	echo "${a[$n]}"
}


# . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . .
# Get the AWS region
function aws_region {
    ec2-metadata --availability-zone | sed -e 's/[^ ]* \(.*\).$/\1/'
}

