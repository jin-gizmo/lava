#!/bin/bash

# ------------------------------------------------------------------------------
# Update /etc/motd
# We definitely don't want to stop boot activity for motd so never exit 1.

PROG=$(basename "$0")

function error {
	[ -t 2 ] && echo "ERROR: $*" >&2
        logger -t "$PROG" -p local0.error "ERROR: $*"
}

# ------------------------------------------------------------------------------

. /etc/os-release


case "${ID}${VERSION_ID}" in
	amzn2)
		/usr/bin/systemctl --quiet restart update-motd || exit 2
		;;
	amzn2023)
		# No special action required
		;;
	*)
		error "Don't know how to handle motd on ${ID}${VERSION_ID} - moving on"
		exit 2  # No exit 1 here folks - allow the boot to continue!!
		;;
esac

exit 0
