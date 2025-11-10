#!/bin/bash

# Cleanup script for Amazon Linux 2023

set -e 

. utils.sh

# . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . .
info Clearing caches and logs
python3 -m pip cache purge > /dev/null 2>&1
rm -rf ~/.cache

yum clean -v all
/bin/rm -rf /var/cache/yum
rm -rf /var/log/lastlog

# . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . .
info /var/cache ...
ls -l /var/cache

# . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . .
info "Deleting stuff we don't need"
/bin/rm -rf /usr/share/man /usr/share/doc
