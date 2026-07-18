#!/bin/bash

# Wait until the Ministack container is ready for service.

CONTAINER=lava-test-ministack

declare -i time_limit start_time end_time

time_limit=60  # seconds
sleep=5
start_time=$(date +%s)
end_time=$((start_time + time_limit))
ministack_url=

# ------------------------------------------------------------------------------
function container_status {
	local status
	status=$(docker inspect --type container --format '{{.State.Status}}' "$1" 2>/dev/null) || echo "not running"
	echo "$status"
}

# ------------------------------------------------------------------------------
echo "🔵 $CONTAINER: checking readiness"

while [ "$(date +%s)" -lt $end_time ]
do
	if [ "$ministack_url" = "" ]
	then
		status="$(container_status "$CONTAINER")"
		case "$status"
		in
			running | healthy)
				port=$(docker exec "$CONTAINER" printenv GATEWAY_PORT)
				ministack_url="http://${CONTAINER}:${port}"
				echo "🟣 $CONTAINER: container $status"
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


	status=$(curl -s -o /dev/null -w "%{http_code}" "${ministack_url}/_ministack/ready") ;
	case "$status"
	in
		000)	echo "🟠 $CONTAINER: service not running" ;;
		200)	echo "✅ $CONTAINER: service ready at $ministack_url (v$version)" && exit 0 ;;
		503)	echo "🟠 $CONTAINER: service initialising" ;;
		*)	echo "❌ $CONTAINER: service in unknown state $status" && exit 1 ;;
	esac
	

	sleep $sleep
done

echo "❌ $CONTAINER: still not ready - giving up"
exit 99
