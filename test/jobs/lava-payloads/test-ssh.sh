#!/bin/bash

# Make sure job includes ....
#
#  "parameters": {
#    "connections": {
#      "ssh": "ssh-conn-id"
#    }
#  },
#
# where "ssh-conn-id" is the SSH connector ID. (Can be called whatever.)

[ $# -ne 1 ] && echo "Usage: $0 repo" >&2 && exit 1
[ "$LAVA_CONN_SSH" == "" ] && echo "LAVA_CONN_SSH not set" >&2 && exit 1

TARGET="$1"

echo "This is an ssh connector test -- getting hostname for $TARGET"
echo ssh connector LAVA_CONN_SSH is $LAVA_CONN_SSH

echo "................................................................................"
cat $LAVA_CONN_SSH || exit 1
echo "................................................................................"

echo
$LAVA_CONN_SSH $TARGET hostname || exit 1
