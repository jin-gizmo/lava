repo_base=..

include $(repo_base)/etc/make/common.mk
include $(repo_base)/etc/make/help.mk

export LAVA_VERSION:=$(shell python3 "$(repo_base)/lava/version.py")
MINISTACK_URL=http://lava-test-ministack:4566
PYTEST_WORKERS=auto

# ------------------------------------------------------------------------------
# Auto-help setup
#
#+ While you *can* run make from this directory, it's generally better to run it
#+ from the parent directory.

#- A typical test sequence might be:
#-
#- `make start`
#-
#- `make load`
#-
#- `make test`
#-
#- `make coverage`
#-
#- `make stop`

HELP_CATEGORY=Miscellaneous targets

# ------------------------------------------------------------------------------
.PHONY: start stop unit up down test coverage refresh

# ------------------------------------------------------------------------------
#:cat Setup targets

up:	start

down:	stop


## Start the docker containers providing test resources.
start:
	jindr start --name jindr
	docker compose --profile build build
	docker compose up --renew-anon-volumes -d

_down:	_stop

_stop:
	docker compose down --volumes

## Stop the docker containers providing test resources.
# We leave jindr running as other stuff could be using it.
stop:	_stop
	@( \
		shopt -s nullglob ; \
		sentinel=$$(mktemp) ; \
		trap 'kill 0; /bin/rm -f "$$sentinel"' INT TERM ; \
		for f in services/*/post.sh ; \
		do \
			{ "$$f" || /bin/rm -f "$$sentinel" ; } & \
		done ; \
		wait ; \
		if [ -f "$$sentinel" ] ; \
		then \
			echo "💚 test infrastructure shutdown complete" ; \
			/bin/rm -f "$$sentinal" ; \
		else \
			echo "❌ One or more test services failed to shutdown correctly" ; \
		fi ; \
	)

## Update source images for test containers.
# Ministack, in particular, updates frequently (almost daily).
refresh:
	docker compose pull --policy always --ignore-buildable
	docker compose --profile build build --pull


# ------------------------------------------------------------------------------
#:cat Test targets

## Run the unit tests.
## Do *make start* first to start up the test infrastructure.
test:	_venv_is_on _aws ready
	pytest -v -s -n "$(PYTEST_WORKERS)"

## Run the unit tests and produce a coverage report.
## Do *make start* first to start up the test infrastructure.
coverage: _venv_is_on _aws ready
	@mkdir -p ../dist/test
	cd .. && pytest --cov=. --cov-report html:dist/test/htmlcov -n "$(PYTEST_WORKERS)"

## Load the test job suite into the ministack container
load:	jobs/venv _ministack_ready
	@( \
		cd jobs ; \
		source venv/bin/activate ; \
		make -j _install env=test ; \
	)

# Ministack returns a 503 on the /_ministack/ready endpoint while its processing
# init scripts and becomes 200 when it's ready.
_ministack_ready:
	@services/ministack/ready.sh

## Check that the local docker based test infrastructure is ready to use (also
## included in the *test* and *coverage* targets).
ready:
	@echo "🔵 Checking docker based test infrastructure readiness"
	@( \
		sentinel=$$(mktemp) ; \
		trap 'kill 0; /bin/rm -f "$$sentinel"' INT TERM ; \
		for f in services/*/ready.sh ; \
		do \
			{ "$$f" || /bin/rm -f "$$sentinel" ; } & \
		done ; \
		wait ; \
		if [ -f "$$sentinel" ] ; \
		then \
			echo "💚 All test services started correctly" ; \
			/bin/rm -f "$$sentinal" ; \
		else \
			echo "❌ One or more test services failed to start correctly" ; \
		fi ; \
	)



jobs/venv:
	VIRTUAL_ENV= make -C jobs init


# ------------------------------------------------------------------------------
#:cat Miscellaneous targets

## Remove ephemeral cruft.
clean:
	docker system prune -f
	docker volume prune -f
	docker network prune -f
	find services/smb/share.x -mindepth 1 -delete
