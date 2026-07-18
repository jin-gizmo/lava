#!/bin/sh

# Ministack only uses /bin/sh for its init scripts which is a pain, so we use
# this wrapper to run our bash scripts.

set -e
echo
echo "--------------------------------------------------------------------------------"
for f in "$(dirname "$0")"/*.bash
do
	echo "Running $f"
	echo "--------------------------------------------------------------------------------"
	/bin/bash "$f"
	echo "--------------------------------------------------------------------------------"
done
