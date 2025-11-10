#!/bin/bash

alias hi=history
alias ..='cd ..; pwd'
alias ...='cd ../..; pwd'
alias ....='cd ../../..; pwd'
alias .....='cd ../../../..; pwd'
alias ......='cd ../../../../..; pwd'
alias -- -='cd -'

alias prot='chmod go='
alias vi=vim
alias p2=python
alias p3=python3

alias l='ls'
alias ll='ls -l'
alias lla='ls -la'
alias la='ls -a'

alias c=ccat
alias ccat=colorize_cat
alias cl=cless
alias cless=colorize_less

# For root we don't have the git and virtualenv aliases. Should not be doing
# that sort of stuff as root.

# Also, have deleted the usual alias of rm/cp/mv to .. -i. That really gives me
# the irits.

# We want to be able to run selected lava utils without putting /usr/local/bin
# in the path.
lava_utils=(
	lava-backup
	lava-check
	lava-dump
	lava-events
	lava-ps
	lava-schema
	lava-stop
	lava-ws
)

LAVA_EXE_PATH=/usr/local/bin
for f in "${lava_utils[@]}"
do
	# shellcheck disable=SC2139
        [ -x "$LAVA_EXE_PATH/$f" ] && alias "$f"="$LAVA_EXE_PATH/$f"
done

unset LAVA_EXE_PATH
