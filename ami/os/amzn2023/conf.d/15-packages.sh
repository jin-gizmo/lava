#!/bin/bash
# ex: sw=4 ts=4 et ai

# ------------------------------------------------------------------------------
# Install a bunch of generally useful packages
# ------------------------------------------------------------------------------

packages=(
    atop  # Good for memory analysis
    bzip2-devel
    cronie
    dos2unix
    lftp  # No old style ftp anymore
    libffi-devel
    nvme-cli
    openldap-clients
    # openssl-devel  # See 25-openssl.sh
    libedit-devel  # Required for Python3 line editing in REPL
    readline-devel  # Required for Python3 line editing in REPL
    sqlite-devel
    telnet
)

# The following are already installed on Amzn 2023
# gpg ... but a minimal version
# hostname
# jq
# util-linux
# wget
# which


# ------------------------------------------------------------------------------
set -e

dnf groupinstall "Development Tools" -y

for p in "${packages[@]}"
do
    dnf install "$p" -y
done

dnf swap gnupg2-minimal gnupg2-full -y
