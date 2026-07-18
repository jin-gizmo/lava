#!/bin/bash

# Do some copies from local/S3 to SMB using lava CLI connector.

# Args are in triples -- msg source dest
overall_rc=0

while [ $# -ge 3 ]
do
	msg="$1"
	src="$2"
	dst="$3"
	shift 3

	echo "$msg: $src --> $dst"
	r=$($LAVA_CONN_SMB put "$src" "$dst" 2>&1)
	rc=$?
	echo "    Status was $rc: $r"
	[ $rc -ne 0 ] && overall_rc=1
done

[ $# -ne 0 ] && echo Ignoring trailing args: $*

exit $overall_rc
