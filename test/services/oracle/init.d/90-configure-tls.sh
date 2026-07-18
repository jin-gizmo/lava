#!/bin/bash

set -e

echo "--------------------------------------------------------------------------------"
echo " $(basename "$0")"
echo "--------------------------------------------------------------------------------"

ORADATA_DIR=/opt/oracle/oradata
WALLET_DIR="${ORADATA_DIR}/wallet"
# shellcheck disable=SC2154
PASSWORD="${ORACLE_PASSWORD}++"  # Must ensure some non-alpha chars in password.
MAX_WAIT=120  # Seconds to wait for listener restart.
WAIT=10   # Seconds between checks for listener restart.
CN="${HOST_CN-localhost}"

mkdir -p "$WALLET_DIR"

orapki wallet create \
    -wallet "$WALLET_DIR" \
    -pwd "$PASSWORD"

# About the "-addext_basic_cons CA" bit ...  Python3.13 changed the way it
# validates certificates. The default SSL context now includes
# VERIFY_X509_STRICT in its default verify flags which means CA certificates
# must have "basicConstraints=critical,CA:TRUE". Certs without the "critical"
# flag or without "CA:TRUE" are rejected.

orapki wallet add \
    -wallet "$WALLET_DIR" \
    -dn "CN=$CN" \
    -keysize 2048 \
    -self_signed \
    -validity 365 \
    -addext_basic_cons CA \
    -pwd "$PASSWORD"

orapki wallet create \
    -wallet "$WALLET_DIR" \
    -auto_login \
    -pwd "$PASSWORD"

# Export the server certificate back outside the container for clients.
orapki wallet export \
    -wallet /opt/oracle/oradata/wallet \
    -dn "CN=$CN" \
    -cert /oracle/server.crt \
    -pwd "${PASSWORD}"

# Update networking to enable TCPS / TLS

install \
    --backup \
    --mode=644 \
    --target-directory=${ORADATA_DIR}/dbconfig/FREE \
    /oracle/*.ora

# Restart the Oracle listener to activate the TCPS listener endpoint.
# Unfortunately, a simple reload will not work here.
echo "Restarting Oracle listener ... "
lsnrctl stop
lsnrctl start

waiting=yes
set -o pipefail
declare -i wait_time=0
while [ "$wait_time" -le "$MAX_WAIT" ]
do
	if lsnrctl status | grep -q 'Service "FREE" has [1-9][0-9]* instance(s)'
	then
		echo " ... FREE service is up"
		waiting=no
		break
	fi
	echo " ... sleeping"
	sleep $WAIT
	wait_time=$((wait_time + WAIT))
done

[ "$waiting" == "yes" ] && \
	echo "WARNING: Out of patience waiting for Oracle listener to restart"

lsnrctl status
