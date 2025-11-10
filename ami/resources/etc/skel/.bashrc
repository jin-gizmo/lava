#!/bin/bash
# shellcheck disable=SC2154
# ex: sw=4 ts=4 et ai

umask 077

for f in env functions aliases
do
    # shellcheck disable=SC1090
    [ -f ~/.bash_"$f".sh ] && . ~/.bash_"$f".sh
done

if [ "$SUDO_USER" != "" -o "$(id -u)" -eq 0 -o "$(id -un)" = "ssm-user" ]
then
    # Remind the user they are in sudo mode or some special account.
    colour=91
    export PS1="\[\e[1;${colour}m\]$(id -nu)@${EC2_INSTANCE_NAME} [\w]\[\e[0m\] "
else
    export PS1="\[\e[1;${colour}m\]${EC2_INSTANCE_NAME} [\w]\[\e[0m\] "
fi

unset colour
