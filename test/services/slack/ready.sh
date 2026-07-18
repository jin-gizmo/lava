#!/bin/bash

# Wait until the vercel emulate Slack service is up and running

CONTAINER=lava-test-slack

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

	version=$(docker exec "$CONTAINER" emulate --version)
	# Get a list of conversations
	result=$(curl -s -X POST "http://localhost:4000/api/conversations.list" \
	  -H "Authorization: Bearer xoxb-fake-token" | jq '.ok')
	status=$?
	if [ $status -eq 0 -a "$result" = "true"  ]
	then
		echo "✅ $CONTAINER: ready (v$version)"
		exit 0
	fi

	echo "🟠 $CONTAINER: slack service not ready (status=$status)"
	sleep $sleep
done

echo "❌ $CONTAINER: still not ready - giving up"
exit 99
