#!/bin/bash

# Get the OS type and major version ... eg. centos8, ubuntu18, darwin18 ...

if [ -f /etc/os-release ]
then
	. /etc/os-release
else
	ID=$(uname -s | tr '[:upper:]' '[:lower:]')
	VERSION_ID=$(uname -r)
fi

[ "$ID" = "" ] && echo "$0: Cannot determine O/S type" >&2 && exit 1
[ "$VERSION_ID" = "" ] && echo "$0: Cannot determine O/S version" >&2 && exit 1

# Get major version
VERSION_ID=$(expr "$VERSION_ID" : '\([^.]*\)')
echo "${ID}${VERSION_ID}"
