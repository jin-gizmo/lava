#!/bin/bash

# Shell commands to be run before any other local custom boot scripts are run.

# EC2 only

# Look for a JSON user data structure containing a "shell0" key.  The value of this
# key must be either a string specifying a command/script to run or a list of
# strings representing a sequence of commands. The execution is done in a
# subshell with stdin redirected from /dev/null, stdout and stderr sent to
# syslog.  If the command sequence exits successfully, syslog level info is
# used, otherwise syslog level error is used.

# Sample userdata:
#	{ "shell": "echo hello world" }
#	{ "shell": ["echo hello world", "echo Resistance is futile > /tmp/borg"] }

/usr/local/sbin/userdata-shell shell0
