#!/bin/bash

# Check that the SMB container is ready.

CONTAINER=lava-test-smb

declare -i time_limit start_time end_time

time_limit=30  # seconds
sleep=2
start_time=$(date +%s)
end_time=$((start_time + time_limit))
container_running=
smb_user=
smb_password=

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
	if [ "$container_running" = "" ]
	then
		status="$(container_status "$CONTAINER")"
		case "$status"
		in
			running | healthy)
				smb_user=$(docker exec "$CONTAINER" printenv SMB_USER)
				smb_password=$(docker exec "$CONTAINER" printenv SMB_PASSWORD)
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


	version=$(docker exec "$CONTAINER" smbd --version)
	result=$(docker exec "$CONTAINER" smbclient --user="$smb_user" \
		--password="$smb_password" --command ls //127.0.0.1/lavatest 2>&1)
	case $?
	in
		0)	echo "✅ $CONTAINER: server ready ($version) ($(($(date +%s) - start_time)) seconds)"
			exit 0
			;;
		*)	echo "🟠 $CONTAINER: $result" ;;
	esac

	sleep $sleep
done

echo "❌ $CONTAINER: still not ready - giving up"
exit 99
