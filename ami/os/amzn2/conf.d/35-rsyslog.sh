#!/bin/bash
# shellcheck disable=SC2016
# ex: sw=4 ts=4 et ai

# ------------------------------------------------------------------------------
# Enable the UDP endpoint for syslog.
# ------------------------------------------------------------------------------

set -e

CONFIG=/etc/rsyslog.conf

sed -i -e '/^# *\$ModLoad  *imudp/s/^# *//' $CONFIG
sed -i -e '/^# *\$UDPServerRun  *514/s/^# *//' $CONFIG

shopt -s nullglob
for f in resources/etc/rsyslog.d/*
do
    install -m644 -oroot -groot "$f" /etc/rsyslog.d
done

systemctl enable rsyslog

# Add /var/log/lava to log rotation
sed -i -e '/^\/var\/log\/messages$/a/var/log/lava' /etc/logrotate.d/syslog
