#!/bin/bash

echo "--------------------------------------------------------------------------------"
echo " $(basename $0)"
echo "--------------------------------------------------------------------------------"

sqlldr userid="${APP_USER}/${APP_USER_PASSWORD}@//localhost:1521/FREEPDB1" \
	control=/oracle/load-custard.ctl \
	skip=1 \
	errors=0 \
	log=/tmp/load-custard.log \
	bad=/tmp/load-custard.bad
