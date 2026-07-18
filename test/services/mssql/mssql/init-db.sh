#!/bin/bash

# Run a bunch of initialisation scripts for our SQL Server DB.
# All .sh and .sql scripts in the specified directory will be run.

# This runs *AFTER* the DB starts

# Usage: init-db.sh dir
#
# The following environment vars must be set:
# - SA_PASSWORD: Password for MS SQL admin user (sa)

PROG="$(basename "$0")"

export DB_HOST=127.0.0.1

# . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . .
function info {
	echo "$PROG: INFO: $*" >&2
}

function warning {
	echo "$PROG: WARNING: $*" >&2
}

function error {
	echo "$PROG: ERROR: $*" >&2
}

function abort {
	echo "$PROG: ABORT: $*" >&2
	exit 1
}

# Check that specified vars are set
function require {
    for i
    do
        [ "${!i}" = "" ] && abort "$i must be set"
    done
}

# . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . .

[ $# -ne 1 ] && error "Usage: $PROG directory" && exit 1
[ ! -d "$1" ] && error "$1: Not a directory" && exit 1

SCRIPTDIR="$1"

require DB_HOST SA_PASSWORD

# . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . .
TMP=$(mktemp -d)
z=1
trap '/bin/rm -rf "$TMP"; exit $z' 0
shopt -s nullglob

set -e

for f in "$SCRIPTDIR"/*
do
	info "Running $f"
	case "$f"
	in
	*.sh)
		"$f"
		;;
	*.sql)
		# Render environment vars into the SQL script.
		ff="${TMP}/$(basename "$f")"
		envsubst < "$f" > "$ff"
		# shellcheck disable=SC2154
		sqlcmd -C -S "$DB_HOST" -U sa -P "${SA_PASSWORD}" -i "$ff"
		;;
	*)	warning "Skipping $f"
		;;
	esac
done
z=0
