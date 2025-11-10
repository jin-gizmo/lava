#!/bin/bash
# ex: sw=4 ts=4 et ai

# ------------------------------------------------------------------------------
# Install a bunch of generally useful packages
# ------------------------------------------------------------------------------

packages=(
    amazon-linux-extras
    bzip2-devel
    dos2unix
    ftp
    gpg
    hostname
    jq
    libffi-devel
    nvme-cli
    openldap-clients
    # openssl-devel  # We build our own now.
    readline-devel  # Required for Python3 line editing in REPL
    sqlite-devel
    telnet
    util-linux
    wget
    which
)

# Amazon Linux Extras
extras=(
    vim
)

# ------------------------------------------------------------------------------
set -e

yum groupinstall "Development Tools" -y

for p in "${packages[@]}"
do
    yum install "$p" -y
done

for p in "${extras[@]}"
do
    amazon-linux-extras install "$p" -y
done
