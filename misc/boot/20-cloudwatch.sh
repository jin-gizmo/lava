#!/bin/bash

# ******************************************************************************
# Update the CloudWatch log config to send /var/log/lava contents to CloudWatch.
#
# Lava workers / dispatchers should be configured to log to the local0 facility.
# This is directed by rsyslog config to /var/log/lava. The config change in this
# file updates the Amazon CloudWatch Agent config to send /var/log/lava to
# CloudWatch logs as:
# 	Log Group:  /var/log/lava/<REALM>
# 	Log Stream: <WORKER>/<INSTANCE ID>
#
# Failure of this process should not stop the boot / lava install process so we
# take care to never exit with status=1.
# ******************************************************************************

PROG=$(basename "$0")

CWATCH_AGENT_DIR=/opt/aws/amazon-cloudwatch-agent
CWATCH_AGENT_CONF="${CWATCH_AGENT_DIR}/etc/config.json"
CWATCH_AGENT_CTL="${CWATCH_AGENT_DIR}/bin/amazon-cloudwatch-agent-ctl"

# ..............................................................................
function info {
	[ -t 2 ] && echo "INFO: $*" >&2
	logger -t "$PROG" -p local0.info "INFO: $*"
}

function error {
	[ -t 2 ] && echo "ERROR: $*" >&2
	logger -t "$PROG" -p local0.error "ERROR: $*"
}

# Usage: abort message
function abort {
	error "ABORT $*"
	exit 2  # No exit 1 here folks!!
}

# ******************************************************************************
[ $# -ne 3 ] && abort "Usage: $PROG s3-source-area realm worker"

# s3source="$1"
realm="$2"
worker="$3"

[ ! -f "$CWATCH_AGENT_CONF" ] && abort "No such file: $CWATCH_AGENT_CONF"

info "Updating CloudWatch Agent configuration file: $CWATCH_AGENT_CONF"

cp "$CWATCH_AGENT_CONF" "${CWATCH_AGENT_CONF}.orig" || abort "Cannot backup $CWATCH_AGENT_CONF"

python3 -c "
import json, sys
conf=json.load(sys.stdin)
conf.setdefault('logs', {}).setdefault('logs_collected', {}).setdefault('files', {}).setdefault('collect_list',[])
conf['logs']['logs_collected']['files']['collect_list'].append(
    {
        'file_path': '/var/log/lava',
        'log_group_name': '/var/log/lava/$realm',
        'log_stream_name': '$worker/{instance_id}'
    }
)
json.dump(conf, sys.stdout, indent=2)
print()
" < "${CWATCH_AGENT_CONF}.orig" > "$CWATCH_AGENT_CONF" || abort "Cannot update $CWATCH_AGENT_CONF"

info "Reloading CloudWatch Agent configuration"

$CWATCH_AGENT_CTL -a fetch-config -m ec2 -c "file:${CWATCH_AGENT_CONF}" -s

[ $? -ne 0 ] && abort "CloudWatch Agent reload failed"

exit 0
