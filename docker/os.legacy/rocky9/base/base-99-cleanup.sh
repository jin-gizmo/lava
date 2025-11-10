#!/bin/bash

# Cleanup script for Rocky Linux.

QUIET=--quiet

dnf remove gcc gcc-c++ -y $QUIET
dnf config-manager --set-disabled crb

python3 -m pip cache purge > /dev/null 2>&1
rm -rf ~/.cache

dnf clean -v all
/bin/rm -rf /var/cache/yum

rm -rf /var/log/lastlog
rm -rf /var/log/dnf*.log

# Get rid of stuff we don't need

/bin/rm -rf /usr/share/man /usr/share/doc
