#!/bin/bash

# Wait until the MySQL container is up and runnning

CONTAINER=lava-test-mysql

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
				db_user=$(docker exec "$CONTAINER" printenv MYSQL_USER)
				db_password=$(docker exec "$CONTAINER" printenv MYSQL_PASSWORD)
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

	
	# The --username and --db-name options on pg_isready don't seem to do anything
	result=$( \
		docker exec -e MYSQL_PWD="$db_password" "$CONTAINER" \
		mysqladmin ping -h 127.0.0.1 --user="$db_user" --connect-timeout=2 2>&1 \
		| head -1 \
		)
	case $?
	in
		0)	echo "🟣 $CONTAINER: $result ($(($(date +%s) - start_time)) seconds)" ;;
		*)	echo "🟠 $CONTAINER: $result" ; sleep $sleep; continue ;;
	esac

	version=$(
		docker inspect "$CONTAINER" \
		| jq -r '.[0].Config.Env[] | select(startswith("MYSQL_VERSION=")) | sub("MYSQL_VERSION="; "")'
	)

	# See if our custom user can run a simple query
	if echo 'select 1' | docker exec -i -e MYSQL_PWD="$db_password" "$CONTAINER" \
		mysql --user="$db_user" --connect-timeout=2 > /dev/null 2>&1
	then
		echo "✅ $CONTAINER: ready (v$version)"
		exit 0
	fi

	echo "🟠 $CONTAINER: waiting for custom data setup"
	sleep $sleep
done

echo "❌ $CONTAINER: still not ready - giving up"
exit 99

