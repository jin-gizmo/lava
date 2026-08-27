# ------------------------------------------------------------------------------
#  Common components for use in other makefiles.
# ------------------------------------------------------------------------------

MAKEFILE_DIR := $(dir $(lastword $(MAKEFILE_LIST)))
include $(MAKEFILE_DIR)/const.mk

ifeq ($(repo_base),)
$(error repo_base not set)
endif

dist=$(repo_base)/dist
etc=$(repo_base)/etc

.DELETE_ON_ERROR:

# DO NOT delete this empty help target.
help:

# ------------------------------------------------------------------------------
# Check virtual environment is not active
_venv_is_off:
	@if [ "$$VIRTUAL_ENV" != "" ] ; \
	then \
		echo "⛔️ Deactivate your virtualenv for this operation" ; \
		exit 1 ; \
	fi

_venv_is_on:
	@if [ "$$VIRTUAL_ENV" == "" ] ; \
	then \
		echo "⛔️ Activate your virtualenv for this operation" ; \
		exit 1 ; \
	fi

# Setup the virtual environment
_venv:	_venv_is_off
	@if [ ! -d venv ] ; \
	then \
		echo "🔵 Creating virtualenv" ; \
		python3 -m venv venv ; \
	fi
	@( \
		echo "🔵 Activating venv" ; \
		source venv/bin/activate ; \
		if [ "$(os)" = "amzn2018" -a "$$PYTHON_INSTALL_LAYOUT" = "amzn" ] ; \
		then \
			echo "⚠️ Aargh - Amazon Linux 1 - pip is broken - unsetting PYTHON_INSTALL_LAYOUT" ; \
			export PYTHON_INSTALL_LAYOUT= ; \
		fi ; \
		echo "🔵 Installing required Python packages" ; \
		python3 -m pip --quiet install 'pip>=20.3' --upgrade ; \
		python3 -m pip --quiet install -r requirements-build.txt --upgrade ; \
		python3 -m pip --quiet install -r requirements.txt --upgrade ; \
		python3 -m pip --quiet install -r requirements-extra.txt --upgrade ; \
	)

# ------------------------------------------------------------------------------
# Make sure we can access AWS.
_aws:
	@aws sts get-caller-identity > /dev/null

# ------------------------------------------------------------------------------
# Repo hygiene stuff
_repo_is_clean:
	@if ! git diff-index --quiet HEAD --; \
	then \
		echo "🔴 Working directory not clean! Commit or stash first."; \
		exit 1; \
	fi

_on_master:
	@if [ "$$(git rev-parse --abbrev-ref HEAD)" != "master" ]; \
	then \
		echo "🔴 Not on master branch!"; \
		exit 1; \
	fi


