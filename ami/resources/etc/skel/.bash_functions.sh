#!/bin/bash
# Functions
# ex: ft=sh

function colorize_cat () {
	[ -z "$COLORIZE_STYLE" ] && COLORIZE_STYLE="emacs" 
	if [ $# -eq 0 ]
	then
		pygmentize -O style="$COLORIZE_STYLE" -g
		return $?
	fi
	local FNAME lexer
	for FNAME in "$@"
	do
		lexer=$(pygmentize -N "$FNAME") 
		if [[ $lexer != text ]]
		then
			pygmentize -O style="$COLORIZE_STYLE" -l "$lexer" "$FNAME"
		else
			pygmentize -O style="$COLORIZE_STYLE" -g "$FNAME"
		fi
	done
}

function colorize_less () {
	[ -z "$COLORIZE_STYLE" ] && COLORIZE_STYLE="emacs" 
	pygmentize -O style="$COLORIZE_STYLE" -g "$@" | command less -R
}
