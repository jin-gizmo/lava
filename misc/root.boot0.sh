#!/bin/bash

# ------------------------------------------------------------------------------
# Boot0 script for a lava worker.
#
# Usage: root.boot0.sh s3-source-area realm worker

PROG=$(basename "$0")

# ------------------------------------------------------------------------------
function info {
	logger -t "$PROG" -p local0.info "INFO: $*"
}

function warning {
	logger -t "$PROG" -p local0.error "WARNING: $*"
}

function error {
	logger -t "$PROG" -p local0.error "ERROR: $*"
}

# ------------------------------------------------------------------------------
info Starting


# If there is a second volume make it into /tmp
TMP_VOL=/dev/xvdb

if [ -b $TMP_VOL ]
then
	result=$(/usr/local/sbin/volprep -m1777 $TMP_VOL /tmp 2>&1)
	if [ $? -eq 0 ]
	then
		info "$result"
	else
		error "$result"
	fi
fi

# If there is a third volume make it the docker storage area /mnt/docker
DOCKER_BASE=/var/lib/docker
DOCKER_VOL=/dev/xvdc

if [ -b $DOCKER_VOL ]
then
	service docker stop || abort Could not stop docker
	[ -e $DOCKER_BASE -a ! -L $DOCKER_BASE ] && mv $DOCKER_BASE $DOCKER_BASE.orig

	# Prep the volume
	result=$(/usr/local/sbin/volprep -l $DOCKER_BASE -m0711 $DOCKER_VOL /mnt/docker 2>&1)
	if [ $? -eq 0 ]
	then
		info "$result"
	else
		error "$result"
	fi

	# Restart docker
	service docker start || about Could not start docker
fi

info Finishing
