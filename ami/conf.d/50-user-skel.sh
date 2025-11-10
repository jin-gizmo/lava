#!/bin/bash
# ex: sw=4 ts=4 et ai

# ------------------------------------------------------------------------------
# Install the skeleton components for new users.
# ------------------------------------------------------------------------------

set -e

# Generic skeleton
cd resources/etc/skel

# Tweak the source (this gets reused later in ami-build.sh)
mkdir -p .postgresql
cp /usr/local/lib/redshift/amazon-trust-ca-bundle.crt .postgresql/root.cert

# Copy for all users
find . | cpio -pduv -R root:root /etc/skel

# Restrict User's home directory mode This will set the skeleton structure
# permissions for all new user's home directory.
/bin/chmod -R 750 /etc/skel
