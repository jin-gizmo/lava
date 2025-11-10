#!/bin/bash
# ex: sw=4 ts=4 et ai

# ------------------------------------------------------------------------------
# Extras. These aren't required to run lava but may be required to build it or
# do other common development tasks.

. lib/funcs.sh

PANDOC_VERSION=2.19.2

# ------------------------------------------------------------------------------
# pandoc -- Required to build the lava doco

PANDOC_FILE="pandoc-${PANDOC_VERSION}-linux-$(arch 3).tar.gz"

(
    set -e
    TMPDIR=$(mktemp -d)
    z=1
    trap '/bin/rm -rf $TMPDIR; exit $z' 0
    cd "$TMPDIR"
    wget "https://github.com/jgm/pandoc/releases/download/${PANDOC_VERSION}/${PANDOC_FILE}"
    tar xf "$PANDOC_FILE" --strip-components 1 -C /usr/local
    z=0
) || abort "pandoc install failed"


# ------------------------------------------------------------------------------
# packer -- Required to build the lava AMI

(
    set -e
    yum install -y yum-utils shadow-utils
    yum-config-manager --add-repo https://rpm.releases.hashicorp.com/AmazonLinux/hashicorp.repo
    yum -y install packer
    yum-config-manager --disable hashicorp > /dev/null
) || abort "packer install failed"

# ------------------------------------------------------------------------------
# cfdoc -- Required to generate CloudFormation doco

(
    set -e
    TMPDIR=$(mktemp -d)
    z=1
    trap '/bin/rm -rf $TMPDIR; exit $z' 0
    cd "$TMPDIR"
    git clone https://murrayandrews_origin@bitbucket.org/murrayandrews/cfdoc.git
    cd cfdoc
    ./install.sh < /dev/null
    z=0
) || abort "cfdoc install failed"
