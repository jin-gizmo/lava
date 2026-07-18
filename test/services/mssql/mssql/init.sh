#!/bin/bash

# This runs *BEFORE* the DB has started and never terminates in order to keep
# the container from exiting.

PROG="$(basename "$0")"

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

require HOST_CN

set -e

# . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . .
# Create a self-signed cert for the DB

# shellcheck disable=SC2154
openssl req -x509 -nodes -newkey rsa:2048 -subj "/CN=${HOST_CN}" -days 365 \
	-keyout /etc/ssl/private/mssql.key \
	-out /etc/ssl/certs/mssql.pem
chmod 444 /etc/ssl/certs/mssql.pem
chmod 400 etc/ssl/private/mssql.key
# Export our cert for clients.
cp /etc/ssl/certs/mssql.pem /mssql/server.crt

# . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . .
# Start the server in the background, give it some time to start then run init scripts.

/opt/mssql/bin/sqlservr &
info "===  Waiting for SQL Server to start  =========================================="
sleep 20
info "===  Initialising SQL Server  =================================================="
/mssql/init-db.sh /docker-entrypoint-initdb.d
info "===  Started and Farted  ======================================================="
tail -f /dev/null

