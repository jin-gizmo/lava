#!/bin/bash

# ------------------------------------------------------------------------------
# Run some lava workers.
#
# This is a sample. Customise as needed.
#
# Usage: run-worker.sh realm worker

PROG=$(basename "$0")
export PATH=/usr/local/bin:$PATH

LAVA_LOG_LEVEL=info
LAVA_LOG=@local0

# ------------------------------------------------------------------------------
lava_args=(
	--daemon
	--level "$LAVA_LOG_LEVEL"
	--log "$LAVA_LOG"
	--heartbeat 60
)


# ------------------------------------------------------------------------------
function info {
	logger -t "$PROG" -p local0.info "INFO: $*"
}

function error {
	logger -t "$PROG" -p local0.error "ERROR: $*"
}

# Usage: abort message
function abort {
	[ -t 2 ] && echo "$PROG: ABORT - $*" >&2
	error "ABORT $*"
	exit 1
}

# ------------------------------------------------------------------------------
[ $# -ne 2 ] && abort Usage: "$PROG realm worker"

realm="$1"
worker="$2"

# ------------------------------------------------------------------------------
# Start our worker daemons.

# Sample -- start 2 worker daemons, each running 3 threads

lava-worker --realm "$realm" --worker "$worker" --threads 3 --tag "lava-$realm-$worker-0" "${lava_args[@]}"
lava-worker --realm "$realm" --worker "$worker" --threads 3 --tag "lava-$realm-$worker-1" "${lava_args[@]}"
