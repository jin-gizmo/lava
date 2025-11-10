#!/bin/bash
# ex: sw=4 ts=4 et ai

# ------------------------------------------------------------------------------
# Reset default umask values
# ------------------------------------------------------------------------------

set -e

/bin/sed -i 's/umask 002/umask 077/g' /etc/profile
/bin/sed -i 's/umask 022/umask 077/g' /etc/profile
