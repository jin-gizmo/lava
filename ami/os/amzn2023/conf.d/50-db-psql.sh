#!/bin/bash
# ex: sw=4 ts=4 et ai

# ------------------------------------------------------------------------------
# Install Postgres CLI
# ------------------------------------------------------------------------------

set -e

dnf install postgresql15 -y

# Need pg_config for PyGreSQL
dnf install libpq-devel -y
