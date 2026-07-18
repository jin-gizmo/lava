#!/bin/bash

# Make sure job includes ....
#
#  "parameters": {
#    "connections": {
#      "sftp": "sftp-conn-id"
#    }
#  },
#
# where "sftp-conn-id" is the sftp connector ID. (Can be called whatever.)

[ $# -ne 1 ] && echo "Usage: $0 repo" >&2 && exit 1
[ "$LAVA_CONN_SFTP" == "" ] && echo "LAVA_CONN_SFTP not set" >&2 && exit 1

TARGET="$1"

echo "This is an sftp connector test -- getting /etc/hosts from $TARGET"
echo sftp connector LAVA_CONN_SFTP is $LAVA_CONN_SFTP

echo "................................................................................"
cat $LAVA_CONN_SFTP || exit 1
echo "................................................................................"

echo
echo get /etc/hosts | $LAVA_CONN_SFTP -b - $TARGET || exit 1
ls -l hosts
