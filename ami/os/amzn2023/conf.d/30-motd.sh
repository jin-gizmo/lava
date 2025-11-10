#!/bin/bash
# ex: sw=4 ts=4 et ai

# ------------------------------------------------------------------------------
# Set the message of the day. This is now done by /usr/sbin/update-motd
# ------------------------------------------------------------------------------

# Disable the default stuff

set -e
shopt -s nullglob

for f in /etc/update-motd.d/*
do
    mv "$f" "$f.orig"
    chmod -x "$f.orig"
done

for f in resources/etc/update-motd.d/*
do
    install -m755 -oroot -groot "$f" /etc/update-motd.d
done

# Get rid of the Amazon Linus 2023 banner.
/bin/rm -f /usr/lib/motd.d/30-banner
