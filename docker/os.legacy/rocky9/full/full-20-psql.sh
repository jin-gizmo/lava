#!/bin/bash

# Install psql CLI

QUIET=--quiet

set -e

. utils.sh
. config.sh


# shellcheck disable=SC2154
PG_REPO="https://download.postgresql.org/pub/repos/yum/reporpms/EL-8-${ARCH1}/pgdg-redhat-repo-latest.noarch.rpm"
dnf -qy module disable postgresql

dnf install "$PG_REPO" -y $QUIET
dnf install postgresql13 git -y $QUIET --nogpgcheck
