#!/bin/bash
# ex: sw=4 ts=4 et ai

# ------------------------------------------------------------------------------
# Install the custom systemctl configs
# ------------------------------------------------------------------------------

set -e

shopt -s nullglob

for f in resources/etc/systemd/system/*
do
    install -m644 -oroot -groot "$f" /etc/systemd/system
done
