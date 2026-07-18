#!/bin/bash

# Wait until the Postgres container is up and runnning

CONTAINER=lava-test-postgres

declare -i time_limit start_time end_time

time_limit=30  # seconds
sleep=2
start_time=$(date +%s)
end_time=$((start_time + time_limit))
db_user=
db_name=

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
	if [ "$db_name" = "" ]
	then
		status="$(container_status "$CONTAINER")"
		case "$status"
		in
			running | healthy)
				db_name=$(docker exec "$CONTAINER" printenv POSTGRES_DB)
				db_user=$(docker exec "$CONTAINER" printenv DB_LAVA_USER)
				[ "$db_name" = "" ] && echo "❌: cannot get database name" && exit 1
				[ "$db_user" = "" ] && echo "❌: cannot get database user" && exit 1
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
		| jq -r '.[0].Config.Env[] | select(startswith("PG_VERSION=")) | sub("PG_VERSION="; "")'
	)
	
	# The --username and --db-name options on pg_isready don't seem to do anything
	status=$(docker exec "$CONTAINER" pg_isready -h 127.0.0.1)
	case $?
	in
		0)	echo "🟣 $CONTAINER: $status ($(($(date +%s) - start_time)) seconds)" ;;
		*)	echo "🟠 $CONTAINER: $status" ; sleep $sleep; continue ;;
	esac

	# See if our custom user can run a simple query
	if docker exec "$CONTAINER" psql -U "$db_user" -d "$db_name" 'select 1' > /dev/null 2>&1
	then
		echo "✅ $CONTAINER: ready (v$version)"
		exit 0
	fi

	echo "🟠 $CONTAINER: waiting for custom data setup"
	sleep $sleep
done

echo "❌ $CONTAINER: still not ready - giving up"
exit 99
