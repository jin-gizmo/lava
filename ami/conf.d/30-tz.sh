#!/bin/bash
# ex: sw=4 ts=4 et ai

# ------------------------------------------------------------------------------
# Set the timezone
# ------------------------------------------------------------------------------

set -e

# shellcheck disable=SC2154
[ "$TIMEZONE" != "" ] && timedatectl set-timezone "$TIMEZONE"

true
