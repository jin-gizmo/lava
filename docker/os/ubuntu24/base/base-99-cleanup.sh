#!/bin/bash

# Cleanup script for Ubuntu

. utils.sh

# . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . .
info Cleaning caches and logs
apt-get clean
rm -f /var/cache/debconf/*old
python3 -m pip cache purge > /dev/null 2>&1
rm -rf ~/.cache
rm -rf /var/log/*log

# . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . .
info "Deleting stuff we don't need"
/bin/rm -rf /usr/share/man /usr/share/doc
