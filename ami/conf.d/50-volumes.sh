#!/bin/bash
# ex: sw=4 ts=4 et ai

# ------------------------------------------------------------------------------
# Any tweaks related to volume configuration goes here
# ------------------------------------------------------------------------------

set -e

# Volume configuration tweaks
cd /usr/lib/systemd/system/

# Remove Amzn2023 /tmp tmpfs volume, keep the /tmp diretory on root
mv tmp.mount tmp.mount.bak
