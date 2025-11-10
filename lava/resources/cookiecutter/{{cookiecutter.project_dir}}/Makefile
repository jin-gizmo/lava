# Create Lava jobs, SQL etc. Relies on the jinja utility.

# Set this if using a custom PyPI repo
PIP_INDEX_URL={{ cookiecutter.pip_index_url }}
GIT_SETUP={% if cookiecutter.git_setup %}_git{% endif %}

#  -- No Jinja rendering below here
# {% raw %}

# ------------------------------------------------------------------------------
# Include bin containing local utils in path
proj_bin := $(dir $(abspath $(lastword $(MAKEFILE_LIST))))bin
export PATH:=$(proj_bin):$(PATH)
SHELL:=/bin/bash

os=$(shell bash bin/os-type)

# ------------------------------------------------------------------------------
.PHONY: dist clean help install uninstall init bin update _git _bin
DIRS=$(wildcard lava-*) misc

# ------------------------------------------------------------------------------
help:
	@echo
	@echo What do you want to make?  Available targets are:
	@echo
	@echo "   init:         Setup the virtual environment."
	@echo "   dist*+:       Make install components but don't install."
	@echo "   diff*:        Compare repo contents to deployed DynamoDB components."
	@echo "   install*+:    Install the lava jobs and payloads."
	@echo "   uninstall*+:  Remove the lava jobs and payloads."
	@echo "   black*:       Format Python code using black."
	@echo "   check*:       Run the pre-commit checks manually."
	@echo "   clean*:       Remove the generated components."
	@echo "   update*:      Update the framework. Requires pkg=new-pkg.zip"
	@echo
	@echo "Targets marked with * require the virtual environment to be"
	@echo "activated and also required an env=<ENV> argument which"
	@echo "identifies the YAML config file config/<ENV>.yaml."
	@echo
	@echo "Targets marked with + accept an optional xattr=no argument"
	@echo "to suppress addition of extended tracking attributes in the"
	@echo "DynamoDB table entries. Don't use this unless required for"
	@echo "compatibility with an older version of the lava worker code."
	@echo
	@echo "You might also need to set the PIP_INDEX_URL environment"
	@echo "variable to point to a private PyPI repo."
	@echo


init: 	_bin _venv $(GIT_SETUP)

_bin:
	@chmod u+x bin/* etc/git-hooks/*

_git:	.git
	git config core.hooksPath etc/git-hooks

.git:
	@echo Initialising git repo
	git init
	git add .
	git commit -m 'Initial commit'


# ------------------------------------------------------------------------------
# Check virtual environment is not active
_no_venv:
	@if [ "$$VIRTUAL_ENV" != "" ] ; \
	then \
		echo Deactivate your virtualenv for this operation ; \
		exit 1 ; \
	fi

# Setup the virtual environment
_venv:	_no_venv
	@if [ ! -d venv ] ; \
	then \
		echo Creating virtualenv ; \
		python3 -m venv venv ; \
	fi
	@( \
		echo Activating venv ; \
		source venv/bin/activate ; \
		export PIP_INDEX_URL=$(PIP_INDEX_URL) ; \
		if [ "$(os)" = "amzn2018" -a "$$PYTHON_INSTALL_LAYOUT" = "amzn" ] ; \
		then \
			echo "Aargh - Amazon Linux 1 - pip is broken - unsetting PYTHON_INSTALL_LAYOUT" ; \
			export PYTHON_INSTALL_LAYOUT= ; \
		fi ; \
		echo Installing requirements ; \
		python3 -m pip install -r etc/requirements.txt --upgrade ; \
		[ -f requirements.txt ] && python3 -m pip install -r requirements.txt --upgrade ; \
		: ; \
	)

# Macro for child makes
define submakes
	@for d in $(DIRS) ; \
	do \
		echo ; \
		echo "[94m$$d ...[0m" ; \
		echo ; \
		$(MAKE) --environment-overrides -C $$d $@ || exit 1 ; \
	done
endef

# ------------------------------------------------------------------------------
ifndef VIRTUAL_ENV
dist install uninstall black check clean update diff:
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

## ------------------------------------------------------------------------------


# Extract the realms table entry
# we don't update the realm info file if it is not empty and less than 1 day old.
_realm_info: _aws
	@( \
		echo -n "Checking realm info for $(REALM) ... " ; \
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
	@echo -n "Checking AWS access ... "
	@aws sts get-caller-identity > /dev/null || exit 1 
	@echo OK

_preflight: _aws _realm_info

dist:	_preflight
	$(submakes)

diff:	_preflight
	@echo
	@echo "[35mDiff checks for realm $(REALM)[0m"
	@echo
	$(submakes)

install: pre-install _install

_install: _preflight
	@echo
	@echo "[35mInstalling to realm $(REALM)[0m"
	@echo
	$(submakes)

# Pre-installation checks
pre-install: check
	@echo
	@echo "[35mPre-install checks for realm $(REALM)[0m"
	@echo
	$(submakes)

uninstall: _preflight
	@echo
	@echo "[91mUninstalling from realm $(REALM)[0m"
	@echo
	$(submakes)

clean:
	$(submakes)

# end ifndef env
endif

black:
	black lava-payloads misc

check:
	etc/git-hooks/pre-commit

ifdef pkg
update:
	@( \
		echo "[34mExtracting updater from new package[0m" ; \
		TMP=$$(mktemp -d) ; \
		z=1 ; \
		trap '$(RM) -r $$TMP; exit $$z' 0 ; \
		unzip -jqud $$TMP $(pkg) '*bin/*' ; \
		chmod 700 $$TMP/* ; \
		export PATH=$$TMP:$$PATH ; \
		$$TMP/update $(pkg) ; \
		z=0 ; \
	)
else
update:
	$(error pkg must be defined. Try make $(MAKECMDGOALS) pkg=...)
endif
#
# end ifndef VIRTUAL_ENV
endif

# {% endraw %}
