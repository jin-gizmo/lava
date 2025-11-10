#!/bin/bash
# ex: sw=4 ts=4 et ai

# ------------------------------------------------------------------------------
# Install Postgres CLI
# ------------------------------------------------------------------------------

set -e

amazon-linux-extras install postgresql14 -y

# Need pg_config for PyGreSQL
yum install libpq-devel -y
