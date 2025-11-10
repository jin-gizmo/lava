#!/bin/bash
# ex: sw=4 ts=4 et ai

# ------------------------------------------------------------------------------
# Setup the root account.
# ------------------------------------------------------------------------------

set -e

# Login/shell setup stuff for root
cd resources/root

find . | cpio -pduvL -R root:root ~root

# Fix up the AWS CLI config for root
cd ~root
umask 077
mkdir -p .aws
cd .aws
/bin/rm -f config
ln -s /usr/local/etc/aws/config .
