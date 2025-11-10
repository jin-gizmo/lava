#!/bin/bash
# ex: sw=4 ts=4 et ai

# ------------------------------------------------------------------------------
# Install the AWS CLI
# ------------------------------------------------------------------------------
#
# ********************       There be dragons here!!!       ********************
#
# Amazon Linux 2 comes with the AWS CLI preinstalled by yum.
#
# But ..... It's python2 so it does not install the awscli Python module for
#           python3 which some other things (like EFS utils) require. So we
#           reinstall the AWS CLI using pip. 
# But ..... We now have 2 versions of python3 and it can be a lottery which one
#           gets run unless you're very careful.
# So ...... We install the stupid thing using pip twice.
# But ..... The two installs put the aws binary in 2 different places (/bin and
#           /usr/local/bin).
# 
# Aaaargghhh.

. lib/funcs.sh

set -e

# Get rid of the Python2 version
yum remove awscli -y

# First install it with the AWS provided version of Python3
/usr/bin/python3 -m pip install awscli

# Remove the vestigial commands in /usr/local/bin
(
    cd /usr/local/bin
    /bin/rm -f aws aws_bash_completer aws.cmd aws_completer aws_zsh_completer.sh
)

# Now install with our version of Python3.
/usr/local/bin/python3 -m pip install awscli

# See if it worked
aws --version
