#!/bin/bash
# ex: sw=4 ts=4 et ai

# ------------------------------------------------------------------------------
# Do a few basic health checks
# ------------------------------------------------------------------------------

export "PATH=/usr/local/bin:$PATH"

status=0

# ------------------------------------------------------------------------------
# General system stuff
openssl version || status=1
python3 --version || status=1
python3 -c 'import sqlite3; print("pysqlite3:", sqlite3.version)' || status=1
python3 -c 'import ssl; print(ssl.OPENSSL_VERSION)' || status=1
aws --version
aws sts get-caller-identity || status=1
docker system info || status=1

# ------------------------------------------------------------------------------
# Database clients
psql --version || status=1
sqlplus -V || status=1
mysql --version || status=1
isql --version || status=1
tsql 2>/dev/null; [ $# -eq 127 ] && echo "No tsql" && status=1

# ------------------------------------------------------------------------------
exit $status
