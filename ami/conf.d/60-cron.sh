#!/bin/bash
# ex: sw=4 ts=4 et ai

# ------------------------------------------------------------------------------
# Install cron.d entries.
# ------------------------------------------------------------------------------

set -e
shopt -s nullglob

for f in resources/cron.d/*
do
    [ -f "$f" ] && install -m644 -oroot -groot "$f" /etc/cron.d
done

# This is required or packer can fail
exit 0
