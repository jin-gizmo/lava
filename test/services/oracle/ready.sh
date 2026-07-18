#!/bin/bash

# Wait until the Oracle container is ready for service. This can take ~90s or so
# due to the delays activating the TLS listener.

CONTAINER=lava-test-oracle

declare -i time_limit start_time end_time

time_limit=120  # seconds
sleep=10
start_time=$(date +%s)
end_time=$((start_time + time_limit))
container_running=

# ------------------------------------------------------------------------------
function container_status {
	local status
	status=$(docker inspect --type container --format '{{.State.Status}}' "$1" 2>/dev/null) || echo "not running"
	echo "$status"
}

# ------------------------------------------------------------------------------
function oracle_version {
	docker exec -i "$CONTAINER" sqlplus -S / AS SYSDBA <<'!'
SET PAGESIZE 0
SET FEEDBACK OFF
SELECT version_full FROM v$instance;
EXIT;
!
}

# ------------------------------------------------------------------------------
echo "🔵 $CONTAINER: checking readiness"

while [ "$(date +%s)" -lt $end_time ]
do
	if [ "$container_running" = "" ]
	then
		status="$(container_status "$CONTAINER")"
		case "$status"
		in
			running | healthy)
				echo "🟣 $CONTAINER: container $status"
				container_running=yes
				;;
			exited)
				echo "❌ $CONTAINER: container $status"
				exit 1
				;;
			*)
				echo "🟠 $CONTAINER: container $status"
				sleep $sleep
				continue
				;;
		esac
	fi

	version=$(
		docker inspect "$CONTAINER" \
		| jq -r '.[0].Config.Env[] | select(startswith("MINISTACK_VERSION=")) | sub("MINISTACK_VERSION="; "")'
	)

	
	docker exec "$CONTAINER" healthcheck.sh
	case $?
	in
		0)
			version=$(oracle_version)
			echo "✅ $CONTAINER: database ready (v$version) ($(($(date +%s) - start_time)) seconds)"
			exit 0
			;;
		1)	echo "🟠 $CONTAINER: database not ready" ;;
		2)	echo "🟠 $CONTAINER: container starting" ;;
		3)	echo "🟠 $CONTAINER: pluggable databases being ... err ... plugged" ;;
		4)	echo "🟠 $CONTAINER: executing user setup scripts" ;;
		5)	echo "🟠 $CONTAINER: executing user startup scripts" ;;
		*)	echo "❌ $CONTAINER: unknown healthcheck status: $status" ; exit "$status" ;;
	esac

	sleep $sleep
done

echo "❌ $CONTAINER: still not ready - giving up"
exit 99
