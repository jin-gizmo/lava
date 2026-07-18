#!/bin/bash

[ $# -ne 1 ] && echo Usage: "$0 exit-status" && exit 1

echo "About to exit with status $1" >&2
exit "$1"
