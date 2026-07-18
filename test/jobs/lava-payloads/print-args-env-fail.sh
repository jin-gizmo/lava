#!/bin/bash

echo Dir is $(pwd)
echo ARGS were /$*/

echo "-- ENVIRONMENT -----------------------------------------------------------------"
env

echo This goes to stderr >&2

exit 1
