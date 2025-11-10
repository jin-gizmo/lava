#!/bin/bash

# Work out what sort of platform we're on using docker conventions.
#


case $(uname -m)
in
	arm64 | aarch64)
		echo linux/arm64
		;;
	x64 | x86_64)
		echo linux/amd64
		;;
	*)
		echo "$(uname -m): Unknown architecture - abort)" >&2
		exit 1
		;;
esac
