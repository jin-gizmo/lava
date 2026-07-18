#!/bin/sh

# No bash here!!

if [ "`/docker-entrypoint-init.d/*`" != '/docker-entrypoint-init.d/*' ]
then
	for f in /docker-entrypoint-init.d/*
	do
		[ ! -x "$f" ] && continue
		echo "Running $f"
		"$f" || exit 1
		echo "--------------------------------------------------"
	done
fi
exec /mailpit "$@"
