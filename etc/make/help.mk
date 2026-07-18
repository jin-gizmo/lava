# ------------------------------------------------------------------------------
# This Makefile invokes the make autohelp awk script. 
# See https://github.com/jin-gizmo/makehelp for more information.
#
# Version: 2.0.0
#
# This script should be included in the Makefile for which autohelp is required.
# Thus:
# 	import help.mk
#
# The following make variables can be set to control behaviour. All of them have
# reasonable defaults.
#
# HELP_CATEGORY
# 	The target category used for the "help" target itself. Set to `none` to
# 	exclude the "help" target from the generated doco.
# HELP_THEME
# 	One of `basic` (the default), `light`, `dark` or `none`.
# HELP_WIDTH
# 	Specify output width for wrapping descriptive text. If not set, the
# 	current terminal width is used.
# HELP_HR
# 	Set to `no`, to disable horizontal rules after any prologue and before
# 	any epilogue.
# HELP_SORT
# 	If set to `alpha`, categories are sorted alphabetically instead of order
# 	of appearance.
# HELP_DEPENDENCIES
# 	If set to `no`, don't include the variable requirements of dependencies
# 	of targets. By default, variable requirements of any dependencies of a
# 	target are add to those of the target itself.
# ------------------------------------------------------------------------------

.DEFAULT_GOAL:=help

.PHONY: help

# := is critical here or MAKEFILE_LIST could be wrong when HELP_DIR is evaluated.
HELP_DIR:=$(abspath $(dir $(lastword $(MAKEFILE_LIST))))

## Print help.
help:	SHELL=/bin/bash
help:	AWK=awk

help:
	@theme="$(HELP_THEME)" ; \
	if [ "$(HELP_THEME)" == "" ]; then \
		if [ ! -t 1 ] ; then \
			theme=none ; \
		else \
			IFS=';' read -r -a fgbg <<< "$${COLORFGBG:-15;0}" ;  \
			theme=dark ; \
			[ "$${fgbg[0]}" -lt "$${fgbg[1]}" ] && theme=light ; \
			colours="$$(tput colors 2>/dev/null || 0)" ; \
			[ "$$colours" -lt 256 ] && theme="$${theme}8" ; \
			[ "$$colours" -lt 8 ] && theme=none ; \
		fi ; \
	fi ; \
	make -pn -f "$(firstword $(MAKEFILE_LIST))" \
		| $(AWK) -f "$(HELP_DIR)/help.awk" -v preprocess=1 \
		| $(AWK) -f "$(HELP_DIR)/help.awk" \
			-v width="$(HELP_WIDTH)" \
			-v theme="$$theme" \
			-v hr="$(HELP_HR)" \
			-v sort_mode="$(HELP_SORT)" \
			-v help_category="$(HELP_CATEGORY)" \
			-v resolve_dependencies="$(HELP_DEPENDENCIES)" \
			- $(MAKEFILE_LIST)

