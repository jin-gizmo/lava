#!/bin/bash
# ex: sw=4 ts=4 et ai

# ------------------------------------------------------------------------------
# Install any /etc/profile.d files
# ------------------------------------------------------------------------------

set -e

shopt -s nullglob

for f in resources/etc/profile.d/*
do
    install -m644 -oroot -groot "$f" /etc/profile.d
done
