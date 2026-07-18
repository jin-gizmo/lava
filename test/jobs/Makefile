# Create Lava jobs, SQL etc. Relies on the jinja utility.

# ------------------------------------------------------------------------------
# Include bin containing local utils in path
# proj_bin := $(dir $(abspath $(lastword $(MAKEFILE_LIST))))bin
proj_bin:=$(abspath .)/bin
export PATH:=$(proj_bin):$(PATH)

# Initialise git on "make init"?
# This is mostly to support lava testing.
GIT:= $(if $(wildcard .no-git),no,yes)


# Do not pass MAKEFILE_LIST down to sub-makes as it will be wrong.
unexport MAKEFILE_LIST

include etc/make/const.mk
include etc/make/help.mk

# ------------------------------------------------------------------------------
# Auto-help setup
#
#+ Welcome to the **lava job framework**. What do you want to make?

#- Except for *init* and *help*, all targets need the virtual environment to be
#- active.
#-
#- Lava job framework version $(FRAMEWORK_VERSION). For more information,
#- consult the lava user guide $(_URL)
#-
#- Help brought to you by **MakeHelp** - https://github.com/jin-gizmo/makehelp.

HELP_CATEGORY=Getting started

# Enforce help ordering
#:cat Getting started
#:cat Build targets
#:cat Installation targets
#:cat Admin targets

# ------------------------------------------------------------------------------
# Set this if using a custom PyPI repo
PIP_INDEX_URL=

FRAMEWORK_VERSION:=$(shell cat etc/version)

## Identifies the YAML config file `config/<ENV>.yaml`.
env=

#  -- No Jinja rendering below here
# 

os:=$(shell bash bin/os-type)

# ------------------------------------------------------------------------------
.PHONY: dist clean help install uninstall init bin update _git _bin
DIRS=$(shell find lava-* -maxdepth 0 -type d) misc

# Grab a random environment name. Yes, this is a kludge for when an env is
# demanded but not used.
ANY_ENV=$(patsubst config/%.yaml,%,$(firstword $(wildcard config/*.yaml)))

# ------------------------------------------------------------------------------
#:cat Getting started

## Setup the virtual environment. This is idempotent and safe to re-run.
init: 	_bin _venv _git

_bin:
	@chmod u+x bin/* etc/git-hooks/*

ifeq ($(GIT),yes)
_git:	.git
	git config core.hooksPath etc/git-hooks

.git:
	@echo "🔵 Initialising git repo"
	git init
	git add .
	git commit -m 'Initial commit'
else
_git:
endif


# ------------------------------------------------------------------------------
# Check virtual environment is not active
_no_venv:
	@if [ "$$VIRTUAL_ENV" != "" ] ; \
	then \
		echo "⛔️ Deactivate your virtualenv for this operation" ; \
		exit 1 ; \
	fi

# Setup the virtual environment
_venv:	_no_venv
	@if [ ! -d venv ] ; \
	then \
		echo "🔵 Creating virtualenv" ; \
		python3 -m venv venv ; \
	fi
	@( \
		echo "🔵 Activating venv" ; \
		source venv/bin/activate ; \
		export PIP_INDEX_URL=$(PIP_INDEX_URL) ; \
		if [ "$(os)" = "amzn2018" -a "$$PYTHON_INSTALL_LAYOUT" = "amzn" ] ; \
		then \
			echo "⚠️ Aargh - Amazon Linux 1 - pip is broken - unsetting PYTHON_INSTALL_LAYOUT" ; \
			export PYTHON_INSTALL_LAYOUT= ; \
		fi ; \
		echo "🔵 Installing required Python packages" ; \
		python3 -m pip --quiet install -r etc/requirements.txt --upgrade ; \
		[ -f requirements.txt ] && python3 -m pip --quiet install -r requirements.txt --upgrade ; \
		: ; \
	)

# Macro for child makes.
# Usage: $(call submakes,key1=v1 key2=v2).
define submakes
	@for d in $(DIRS) ; \
	do \
		echo ; \
		$e "$B$$d ...$_" ; \
		echo ; \
		$(MAKE) --environment-overrides -C $$d $@ $(1) || exit 1 ; \
	done
endef

# Macro for child makes without aborting a failed stage
# Usage: $(call submakes-no-abort,key1=v1 key2=v2).
define submakes-no-abort
	@status=0 ; \
	for d in $(DIRS) ; \
	do \
		echo ; \
		$e "$B$$d ...$_" ; \
		echo ; \
		$(MAKE) --environment-overrides -C $$d $@ $(1) || status=1 ; \
	done ; \
	exit "$$status"
endef

# ------------------------------------------------------------------------------
ifndef VIRTUAL_ENV
dist install uninstall black check clean update diff set-schema:
	$(error You need to activate the virtual environment)
else

ifndef env
dist pre-install _install install uninstall clean diff:
	$(error env must be defined. Try make $(MAKECMDGOALS) env=...)
else

# Check that config file exists
ifeq (,$(wildcard config/$(env).yaml))
$(error config/$(env).yaml: No such file)
endif

# Extract some parameters from the config
REALM=$(shell echo '+{realm}+' | bin/jinja -d + --file config/$(env).yaml)
REALM_INFO=dist/$(env)/.realm.json

ifeq ($(S3_PAYLOADS),None)
$(error $(REALM): Unknown realm)
endif

# Export environment for child makes
export

# ------------------------------------------------------------------------------


# Extract the realms table entry
# we don't update the realm info file if it is not empty and less than 1 day old.
_realm_info: _aws
	@( \
		echo -n "🔵 Checking realm info for $(REALM) ... " ; \
		if [[ -n $$(find "$(REALM_INFO)" -type f -size +0c -mtime -1 2>/dev/null) ]] ; \
		then \
			echo "using cache" ; \
		else \
			echo -n "updating ... " ; \
			mkdir -p "dist/$(env)" ; \
			dyn-get-item --table lava.realms --container lava.realm "realm=$(REALM)" > "$(REALM_INFO)" ; \
			status=$$? ; \
			[ "$$status" -ne 0 ] && $(RM) "$(REALM_INFO)" ; \
			[ "$$status" -eq 2 ] && echo "No such realm: $(REALM)" && exit 1 ; \
			[ "$$status" -ne 0 ] && exit 1 ; \
			echo done ; \
		fi ; \
	)

# Make sure we can get to AWS
_aws:	
	@echo -n "🔵 Checking AWS access ... "
	@aws sts get-caller-identity > /dev/null || exit 1 
	@echo OK

# ------------------------------------------------------------------------------
#:cat Build targets

_preflight: _aws _realm_info

## Make install components but don't install.
#:req env
dist:	_preflight
	$(call submakes)

## Compare repo contents to deployed DynamoDB components.
#:cat Build targets
#:req env
diff:	_preflight
	@echo
	@$e "$M🟣 Diff checks for realm $(REALM)$_"
	@echo
	$(call submakes-no-abort)

# ------------------------------------------------------------------------------
#:cat Installation targets

## Install the lava jobs and payloads.
#:req env
install: pre-install _install

_install: _preflight
	@echo
	@$e "$M🟣 Installing to realm $(REALM)$_"
	@echo
	$(call submakes)

## Run the pre-install checks manually. These are also run as part of the
## *install* target.
#:req env
pre-install: check
	@echo
	@$e "$M🟣 Pre-install checks for realm $(REALM)$_"
	@echo
	$(call submakes-no-abort)

## Remove the lava jobs and payloads from AWS.
#:req env
uninstall: _preflight
	@echo
	@$e "$M🟣 Uninstalling from realm $(REALM)$_"
	@echo
	$(call submakes)

# ------------------------------------------------------------------------------
#:cat Admin targets

## Remove the generated components locally.
clean:
	$(call submakes)

# end ifndef env
endif

## Format Python code using **black**.
black:
	black lava-payloads misc

## Run the pre-commit checks manually. These are also run as part of the
## *install* target.
check:
	etc/git-hooks/pre-commit

## Update the framework. The *pkg* argument should point to wherever the upgrade
## ZIP package is stored in the local filesystem.
#:req pkg=lava-job-framework-<VERSION>.zip
ifdef pkg
update:
	@( \
		$e "$B🔵 Extracting updater from new package$_" ; \
		TMP=$$(mktemp -d) ; \
		z=1 ; \
		trap '$(RM) -r $$TMP; exit $$z' 0 ; \
		unzip -jqud $$TMP $(pkg) '*bin/*' ; \
		chmod 700 $$TMP/* ; \
		export PATH=$$TMP:$$PATH ; \
		python3 -m pip install cookiecutter -U ; \
		$$TMP/update $(pkg) ; \
		z=0 ; \
	)
else
update:
	$(error pkg must be defined. Try make $(MAKECMDGOALS) pkg=...)
endif

set-schema:
	@echo
	@$e "$M🟣 Updating \$$schema entries$_"
	@echo
	$(call submakes,env=$(ANY_ENV))

# end ifndef VIRTUAL_ENV
endif

