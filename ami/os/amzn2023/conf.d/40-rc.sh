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
#!/bin/bash

export PATH=/usr/local/bin:$PATH

for f in /usr/local/etc/rc.d/*
do
    logger -t rclocal -p local0.info run $f
    $f
done
!

chmod 755 /etc/rc.local

# Amazon Linux 2023 specials ...

ln -s /etc/rc.local /etc/rc.d
ls -lL /etc/rc.d

# This looks odd but what we're doing here is enabling the pre-defined template
# service spec for rc-local in /usr/lib/systemd/system/rc-local.service. This
# cannot be "enabled" directly because the template does not have a "WantedBy"
# value so systemctl can't work out where to put it. The following command
# creates the necessary symlink so it is enabled.
systemctl add-wants multi-user.target rc-local
