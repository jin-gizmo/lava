#!/bin/bash

# User specific environment and startup programs

export PATH=$PATH:$HOME/.local/bin:$HOME/bin

# Get the value of a tag on the ec2 instance
function tag {
	# ec2tags will hang on nodes with no path to the EC2 endpoints.
	# So we allow the user to interrupt it.
	local value='??'
	trap 'echo Interrupt' 2
	value=$(ec2tags --cli-connect-timeout 3 --cli-read-timeout 3 "{$1}")
	trap 2
	echo "$value"
}

# ------------------------------------------------------------------------------
# Get some environment / instance info

trap "env='??';EC2_INSTANCE_NAME='??'" 2
echo "Getting environment info (ctrl-C to cancel) ...\\c"
env=$(tag environment | tr '[:upper:]' '[:lower:]')
EC2_INSTANCE_NAME=$(tag Name)
trap 2

colour=35  # Magenta if env is unknown
[[ "$env" =~ dev.* ]] && colour=34	# dev - blue
[[ "$env" =~ prod.* ]] && colour=31	# prod - red

#boot_time=$(last reboot| sed 's/.*amz \(.*\)  *-.*/\1/;q')
#echo -e "\e[${colour}mBooted:   ${boot_time}\e[0m"
zone=$(ec2-metadata --availability-zone)
instance=$(ec2-metadata --instance-id)

echo -e "\e[${colour}mUptime:   $(uptime -p | cut -d' ' -f2-)\e[0m"
echo -e "\e[${colour}mAZ:       ${zone#* }\e[0m"
echo -e "\e[${colour}mInstance: ${instance#* } (${EC2_INSTANCE_NAME})\e[0m"

set -- $SSH_CONNECTION
echo -e "\e[${colour}mConn:     $1 --> $3\e[0m"
echo

[ "${EC2_INSTANCE_NAME}" == "" ] && EC2_INSTANCE_NAME=${instance#* }
export EC2_INSTANCE_NAME

# ------------------------------------------------------------------------------
if [ -f ~/.bashrc ]; then
	. ~/.bashrc
else
	:
fi
