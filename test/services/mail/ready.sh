#!/bin/bash

# Wait until the Mailpit SMTP service is up and running

CONTAINER=lava-test-mail

declare -i time_limit start_time end_time

time_limit=30  # seconds
sleep=2
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
echo "🔵 $CONTAINER: checking readiness"

set -o pipefail

while [ "$(date +%s)" -lt $end_time ]
do
	if [ "$container_running" = "" ]
	then
		status="$(container_status "$CONTAINER")"
		case "$status"
		in
			running | healthy)
				container_running=yes
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

	version=$(curl -s -X GET "http://$CONTAINER:8025/api/v1/info" \
		-H 'accept: application/json' | jq --raw-output '.Version')
	status=$?
	if [ $status -eq 0 -a "$version" != ""  ]
	then
		echo "✅ $CONTAINER: ready ($version)"
		exit 0
	fi

	echo "🟠 $CONTAINER: Mailpit SMTP service not ready (status=$status)"
	sleep $sleep
done

echo "❌ $CONTAINER: still not ready - giving up"
exit 99
