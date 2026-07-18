#!/bin/bash

# Wait until the Microsoft Server (mssql) container is up and runnning

CONTAINER=lava-test-mssql

declare -i time_limit start_time end_time

time_limit=60  # seconds
sleep=5
start_time=$(date +%s)
end_time=$((start_time + time_limit))
db_user=
db_password=

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
	if [ "$db_user" = "" ]
	then
		status="$(container_status "$CONTAINER")"
		case "$status"
		in
			running | healthy)
				db_user=$(docker exec "$CONTAINER" printenv DB_LAVA_USER)
				db_password=$(docker exec "$CONTAINER" printenv DB_LAVA_PASSWORD)
				[ "$db_user" = "" ] && echo "❌: cannot get database user" && exit 1
				[ "$db_password" = "" ] && echo "❌: cannot get database password" && exit 1
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

	# See if our custom user can run a simple query
	# Note we cannot use `head -1` here because it will close the pipe for sqlcmd too early.
	version=$(
		docker exec "$CONTAINER" \
			sqlcmd -C -W -h -1 -S 127.0.0.1 -U "$db_user" -P "$db_password" \
				-Q "SET NOCOUNT ON; SELECT SERVERPROPERTY('ProductVersion')" 2>&1 \
		| sed -n 1p
	)
	if [ $? -eq 0 ]
	then
		echo "✅ $CONTAINER: ready (v$version)"
		exit 0
	fi

	echo "🟠 $CONTAINER: $version"
	sleep $sleep
done

echo "❌ $CONTAINER: still not ready - giving up"
exit 99

