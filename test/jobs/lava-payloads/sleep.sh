#!/bin/bash

[ $# -ne 1 ] && echo Usage: $0 seconds && exit 1

echo Sleeping for $1 seconds
sleep $1
echo Sleep over
