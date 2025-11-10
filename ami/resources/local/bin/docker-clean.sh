#!/bin/bash

# Prune docker storage. More aggressive pruning is done if storage consumption
# is above a specified threshold %.

declare -i threshold=50

USAGE="Usage: $0 [THRESHOLD-PERCENT]"

case $# in
	0)	;;
	1)	! [[ "$1" =~ ^[0-9]+$ ]] && echo "$USAGE" >&2 && exit 1
		threshold="$1"
		;;
	*)	echo "$USAGE" >&2 && exit 1
		;;
esac

docker_root="$(docker info -f '{{.DockerRootDir}}')"
[ ! -d "$docker_root" ] && echo "$docker_root is not a directory" && exit 1

set -e

# shellcheck disable=SC2046
set -- $(df --output=pcent "$docker_root")
pct_used="${2%\%}"
[ "$pct_used" -ge "$threshold" ] && purge_all="-a"

# shellcheck disable=SC2086
docker system prune -f $purge_all
