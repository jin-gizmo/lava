#!/bin/bash

# Install psql CLI

QUIET=--quiet

set -e

. utils.sh
. config.sh

info Installing MySQL
apt-get install postgresql-client -y $QUIET
