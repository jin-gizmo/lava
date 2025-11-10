#!/bin/bash

# ------------------------------------------------------------------------------
# Lava worker boot script to check for security updates

SEC_UPDATES=yes
# Reboot if security updates applied - yes or no
# Set this to no if you want the node to work. Set it to yes if you want the
# node to die horribly with a kernel panic or drop into grub on boot.
REBOOT=no

# Set this to 1 to abort the boot setup process if sec updates fail or 2 if the
# node can continue in the event of failure.
FAIL_EXIT=2

# This is for retries. Yum updates can fail early in boot sequence due to
# competition from AWS ssm_agent. (Credit Daniel Gomes). Values are sleep
# seconds. The first one should be 0.
BACKOFF=(0 5 10)

PROG=$(basename "$0")

# ------------------------------------------------------------------------------
function info {
	[ -t 2 ] && echo "INFO: $*" >&2
	logger -t "$PROG" -p local0.info "INFO: $*"
}

function error {
	[ -t 2 ] && echo "ERROR: $*" >&2
	logger -t "$PROG" -p local0.error "ERROR: $*"
}

# Usage: abort message
function abort {
	error "ABORT $*"
	exit $FAIL_EXIT
}

# ------------------------------------------------------------------------------
if [ "$SEC_UPDATES" == "yes" ]
then
	info "Checking for security updates"
	yum check-update --security
	case $? in
	0)
		info "No security updates needed"
		;;
	100)
		info "Installing security updates"
		updates_ok=
		for zzz in "${BACKOFF[@]}"
		do
			[ "$zzz" -ne 0 ] && info "Sleeping for $zzz seconds before retry"
			sleep "$zzz"
			yum update --security -y && info "Security updates done" \
				&& updates_ok=yes && break
			error "Security update failed with status $?"
		done
		[ "$updates_ok" != "yes" ] && abort "Security updates failed and no more retries"

		if [ "$REBOOT" == "yes" ]
		then
			[ -f /NO-REBOOT ] && abort "Possible reboot loop detected -- reboot cancelled"
			info "Rebooting"
			# Create sentinel to prevent another reboot
			touch /NO-REBOOT || abort "Cannot create /NO-REBOOT guard file -- reboot cancelled"
			reboot
			exit 0
		fi
		;;
	*)
		abort "yum check-update exited with status $?"
		;;
	esac

	# We only reach this point if there was no reboot -- ok to remove our sentinel
	/bin/rm -f /NO-REBOOT
fi

exit 0
