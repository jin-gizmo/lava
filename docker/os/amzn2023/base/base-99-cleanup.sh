#!/bin/bash

# Cleanup script for Amazon Linux 2023

QUIET=--quiet

. utils.sh
. config.sh

# ------------------------------------------------------------------------------

PKGS_TO_DELETE=(
	gcc
	gcc-c++
	bison
	byacc
	subversion
	automake
	autoconf
	xorg-x11-fonts-ISO8859-1-100dpi
)

# . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . .
info Removing superfluous packages
dnf remove "${PKGS_TO_DELETE[@]}" -y $QUIET

# . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . .
info Clearing caches and logs
python3 -m pip cache purge > /dev/null 2>&1
rm -rf ~/.cache
dnf clean -v all
/bin/rm -rf /var/cache/dnf
rm -rf /var/log/lastlog

# . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . .
info /var/cache ...
ls -l /var/cache

# . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . .
info "Deleting stuff we don't need"
/bin/rm -rf /usr/share/man /usr/share/doc

info "Cleanup complete"
