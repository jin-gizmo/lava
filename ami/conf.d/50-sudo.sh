#!/bin/bash
# ex: sw=4 ts=4 et ai

# ------------------------------------------------------------------------------
# Modify sudo setup
# ------------------------------------------------------------------------------

set -e

# We want to allow the EC2_INSTANCE_NAME environment var to be passed via sudo
# as that is used in the PS1 prompt.

sed -i.orig -e '/^Defaults\s\s*env_keep\s*=/aDefaults    env_keep += "EC2_INSTANCE_NAME"' /etc/sudoers
