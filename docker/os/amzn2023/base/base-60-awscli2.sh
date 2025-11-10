#!/bin/bash
# shellcheck disable=SC2154

# Can't install the AWS CLI from the Amazon Linux repo because we are using our
# own Python version and PYTHONPATH. So install in the generic linux way.

set -e

. utils.sh

require ARCH1


# ------------------------------------------------------------------------------
TMP=$(mktemp -d)
z=1
trap '/bin/rm -rf $TMP; exit $z' 0

set -x
cd "$TMP"
info "AWS CLI v2 - package download"
wget --no-verbose "https://awscli.amazonaws.com/awscli-exe-linux-${ARCH1}.zip"
ls -l

unzip "awscli-exe-linux-${ARCH1}.zip"

info "AWS CLI v2 - install"
aws/install
aws --version

z=0
