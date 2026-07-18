#!/bin/bash

# Make sure job includes ....
#
#  "parameters": {
#    "connections": {
#      "git": "m-git"
#    }
#  },
#
# where "m-git" is the git connector ID. (Can be called whatever.)

[ $# -ne 1 ] && echo "Usage: $0 repo" >&2 && exit 1
[ "$LAVA_CONN_GIT" == "" ] && echo "LAVA_CONN_GIT not set" >&2 && exit 1

REPO="$1"

echo "This is a git connector test -- cloning $REPO"
echo git connector LAVA_CONN_GIT is $LAVA_CONN_GIT

echo "................................................................................"
cat $LAVA_CONN_GIT || exit 1
echo "................................................................................"

echo
$LAVA_CONN_GIT clone "$REPO" repo || exit 1

echo Here is my repo
echo "................................................................................"
ls -l repo || exit 1
echo "................................................................................"
