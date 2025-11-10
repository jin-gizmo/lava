#!/bin/bash
# ex: sw=4 ts=4 et ai

# ------------------------------------------------------------------------------
# Install the instance boot scripts in /usr/local/etc/rc.d
# ------------------------------------------------------------------------------

set -e

# Install the scripts
shopt -s nullglob
mkdir -p /usr/local/etc/rc.d

for f in resources/local/rc.d/*
do
    install -m755 -oroot -groot "$f" /usr/local/etc/rc.d
done

# Make the rc.d scripts run from /etc/rc.local at boot time.
cat >> /etc/rc.local <<"!"

export PATH=/usr/local/bin:$PATH

for f in /usr/local/etc/rc.d/*
do
    logger -t rclocal -p local0.info run $f
    $f
done
!

chmod 755 /etc/rc.local
