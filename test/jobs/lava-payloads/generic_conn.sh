#!/bin/sh

# Print out the contents of a generic connector

echo This is the contents of the generic connector $LAVA_CONNID_GENERIC

for item in a b c d e f g h
do
	echo "-----"
	echo $item: $($LAVA_CONN_GENERIC $item)
done
echo "-----"
