# ex: cc=80,95

SHELL:=/bin/bash

repo_base=.

include $(repo_base)/etc/Makefile

APP=lava

# Too many workers actually slows it down.
PYTEST_WORKERS=auto
# PYTEST_WORKERS=2

# This is the name of an index server for twine uploads in ~/.pypirc
pypi=pypi

LAVA_VERSION=$(shell python3 lava/version.py)

# ------------------------------------------------------------------------------
#  Generic from here on

override OS=$(shell $(etc)/os-type.sh)
override PY_VER=$(shell python3 -c 'from sys import version_info as v; print(f"{v.major}.{v.minor}")')
override ARCH=$(shell arch)
override RUNTIME:=$(OS)-py$(PY_VER)
runtime=$(RUNTIME)

# This won't be called if platform is set on command line
platform:=$(shell $(etc)/docker-platform.sh)

PKG_OS_DIR=$(dist)/pkg/$(OS)
PKG=$(PKG_OS_DIR)/$(APP)-$(LAVA_VERSION)-$(runtime)-$(ARCH).tar.bz2

LIB_PKG=$(dist)/jinlava/$(APP)-$(LAVA_VERSION).tar.gz

# Requirements.txt handling
PIP_FILES=$(wildcard req*.in)
REQ_FILES=$(foreach P,$(PIP_FILES:.in=.txt),$(P))

SOURCE_FILES=$(wildcard *.py) $(shell find lava -name '*.py') $(wildcard $(etc)/*.sh) \
	$(REQ_FILES) MANIFEST.in

HIDDEN_PYTHON=$(shell \
	find . -type f -perm +u=x ! -name '*.py' ! -name '*.sh' ! -path './venv/*' \
			! -path './.??*/*' ! -path './doc/*' ! -path './untracked/*' \
			! -path './dist/*' ! -path './*egg-info*' \
		-print0 | xargs -0 file | grep 'Python script' | cut -d: -f1)

USER_GUIDE=$(subst %,$(fmt),lava-user-guide.%)
config=deploy.yaml

# Set to empty to not include non-standard module in the package.
INCLUDE_MODULES=-m

ifneq ($(wildcard test/*),)
TESTS=yes
else
TESTS=no
endif

.PHONY: help deploy backup doc clean list pkg jinlava lambda all ami init upgrade spell test cfn oracle

# ------------------------------------------------------------------------------
help:
	@echo
	@$e What do you want to make?  Available targets are:
	@echo
	@$e "$RGetting started$_"
	@$e "   help:      Print this help text."
	@$e "   init:      Initialise the project (create venv etc.) Non-destructive."
	@$e "   oracle:    Download / update the Oracle client binaries."
	@echo
	@$e "$RBuild related targets:$_"
	@$e "   builder$C^+$_: Build a multi-platform docker image that can build the lava worker"
	@$e "              install package for the specified runtime on foreign platforms."
	@$e "              ARM (linux/arm64) and x86 (linux/amd64) are supported."
	@$e "   cfn:       Make the CloudFormation templates and documentation."
	@$e "   lambda:    Make the lambda function code bundles."
	@$e "   jinlava:   Create a source distribution of the lava libraries suitable for"
	@$e "              installation using pip."
	@$e "   pkg$C^+$_:     Make the lava worker install package."
	@$e "   registry:  Start a local docker registry to hold multi-plaftorm images for"
	@$e "              building foreign platform builds. The registry is managed by the"
	@$e "              \"jindr\" utility. Try \"jindr --help\" for more information."
	@echo
	@$e "$RInstallation related targets:$_"
	@$e "   deploy:    Deploy modified files to S3. The env=<ENVIRONMENT>"
	@$e "              argument is mandatory. It specifies a target environment"
	@$e "              configuration in config.yaml. The optional config=<FILE>"
	@$e "              argument can specify a different config file."
	@$e "   pypi:      Upload the jinlava pkg to the \"$(pypi)\" PyPI server via twine."
	@$e "              The \"$(pypi)\" server must be defined in ~/.pypirc. Add pypi=..."
	@$e "              to specify a different index server entry in ~/.pypirc."
	@echo
	@$e "$RUser guide / documentation targets$_"
	@$e "   doc:       Make the user guide into consolidated markdown."
	@$e "   preview:   Build and preview the mkdocs version of the user guide."
	@$e "   publish:   Publish the user guide to GitHub pages (must be on master branch)."
	@$e "   spell:     Spell check the user guide (requires aspell)."
	@echo
	@$e "$RMiscellaneous targets:$_"
	@$e "   upgrade:   Upgrade the virtualenv with latest packages."
	@$e "   clean:     Remove the generated packages and documents."
	@$e "   freeze:    Make frozen requirements.txt files based on versions currently"
	@$e "              installed in the venv."
	@$e "   tools:     Build the dev tools."
	@$e "   black:     Format the code using black."
	@$e "   check:     Run some code checks (flake8 etc)."
	@$e "   count:     Do line counts on source code (needs tokei)."
	@echo
ifeq ($(TESTS),yes)
	@$e "$RTesting targets$_"
	@$e "   coverage:  Run the unit tests and produce a coverage report."
	@$e "   test:      Run the unit tests."
	@$e "   start/up:  Start the docker containers providing test resources."
	@$e "   stop/down: Stop the docker containers providing test resources."
	@echo
endif
	@echo
	@$e "Targets with $C^$_ accept an optional $iruntime=<RUNTIME>$_ argument where $i<RUNTIME>$_"
	@$e "specifies the target O/S type and Python version. On the current machine, this"
	@$e "value defaults to \"$(RUNTIME)\". Building for a foreign runtime is done in a"
	@$e "docker container. See etc/builders for Dockerfiles. Builders are available for"
	@$e "the following runtimes:"
	@( \
		for b in $(wildcard etc/builders/*.Dockerfile) ; \
		do \
			$e "    - $$(basename $${b%.Dockerfile})" ; \
		done ; \
	)
	@echo
	@$e "Targets with a $C+$_ accept an optional $iplatform=<PLATFORM>$_ argument. This specifies"
	@$e "the target platform architecture in docker terminology (e.g. linux/amd64 or"
	@$e "linux/arm64)."
	@echo

# ------------------------------------------------------------------------------


FORCE:

# We want these to build always as the venv could have something new in it.
# However we take care to not replace the .txt file if its unchanged to minimise
# unnecessary rebuilds.
%.txt:	FORCE
	@( \
		if [ "$(_freeze)" == "no" ] ; \
		then \
			echo Skipping pip freeze for $@ ; \
			exit 0; \
		else \
			true ; \
		fi ; \
		z=0; TMP=$$(mktemp) ; trap '/bin/rm -f $$TMP; exit $$z' 0 ; \
		$(etc)/pip-freeze < $*.in > $$TMP || exit ; \
		if cmp -s $@ $$TMP ; \
		then \
			echo $@ is up to date: ; \
		else \
			cp $$TMP $@ ; \
			echo Updating $@ ; \
		fi ; \
		z=0 ; \
	)


ifndef env
deploy:
	$(error You must specify env=... argument!)
else
deploy:
	$(etc)/deploy.sh -e $(env) -f $(config)
endif

# ------------------------------------------------------------------------------
# Check virtual environment is not active
_no_venv:
	@if [ "$$VIRTUAL_ENV" != "" ] ; \
	then \
		$e "$RDeactivate your virtualenv for this operation$_" ; \
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
		if [ "$(os)" = "amzn2018" -a "$$PYTHON_INSTALL_LAYOUT" = "amzn" ] ; \
		then \
			echo "Aargh - Amazon Linux 1 - pip is broken - unsetting PYTHON_INSTALL_LAYOUT" ; \
			export PYTHON_INSTALL_LAYOUT= ; \
		fi ; \
		echo Installing requirements ; \
		python3 -m pip install 'pip>=20.3' --upgrade ; \
		python3 -m pip install -r requirements-build.txt --upgrade ; \
		python3 -m pip install -r requirements.txt --upgrade ; \
		python3 -m pip install -r requirements-extra.txt --upgrade ; \
	)

# ------------------------------------------------------------------------------

init:	_venv

_pkg:	$(PKG)

# If target O/S matches current, do a local build. Otherwise try to build in
# a container. See $(etc)/builders for dockerfiles for supported O/S.
# Note that we set PIP_INDEX_URL env var in the build to mimic pip behavour on
# the current host.

$(PKG):	$(SOURCE_FILES)
	@if [ "$(RUNTIME)" != "$(runtime)" -a ! -f /.dockerenv ] ; \
	then \
		[ ! -f "$(etc)/builders/$(runtime).Dockerfile" ] && \
			echo Unsupported foreign runtime: $(runtime) >&2 && exit 1 ; \
		builder="localhost:$(REGISTRY_LOCAL_PORT)/build/lava/$(runtime)" ; \
		if ! docker images --format "{{.Repository}}" | grep -q "$$builder" ; \
		then \
			echo "No builder available for runtime=$(runtime). Try:" ; \
			echo "    docker pull localhost:$(REGISTRY_LOCAL_PORT)/build/lava/$(runtime)" ; \
			echo "or ..." ; \
			echo "    make builder runtime=$(runtime)" ; \
			exit 1 ; \
		fi ; \
		$e "$GForeign container build for $(runtime) (platform=$(platform))$_" ; \
		export PIP_INDEX_URL="$(shell $(etc)/pip-index-url)" ; \
		docker run --rm -t --user $(shell id -u):$(shell id -g) -w /lava/build \
			-v$$(pwd):/lava/build -v ~/.aws:/lava/.aws \
			-e PIP_INDEX_URL \
			--platform "$(platform)" \
			"$$builder" \
			make _pkg _freeze=no ; \
	else  \
		$e "$GLocal build for $(runtime)$_" ; \
		env | grep PIP_INDEX ; \
		[ ! -d $(PKG_OS_DIR) ] && mkdir -p $(PKG_OS_DIR) ; \
		$(etc)/pkg.sh -f $@ $(INCLUDE_MODULES) || $(RM) $(PKG) ; \
		$e "$bCreated $@$_" ; \
	fi


# ------------------------------------------------------------------------------
ifndef VIRTUAL_ENV
all pkg freeze ami lambda jinlava doc tools black check upgrade cfn oracle:
	$(error You need to activate the virtual environment)
else

pkg:	freeze _pkg


upgrade:
	python3 -m pip install -r requirements-build.txt --upgrade
	python3 -m pip install -r requirements.in --upgrade
	python3 -m pip install -r requirements-extra.in --upgrade
	
freeze:	$(REQ_FILES)


cfn:
	$(MAKE) -C cfn $(MAKECMDGOALS) dist=$(abspath $(dist))

lambda:
	$(MAKE) -C lambda $(MAKECMDGOALS) dist=$(abspath $(dist))

jinlava: $(LIB_PKG)

$(LIB_PKG): $(SOURCE_FILES)
	@mkdir -p $(dist)/jinlava
	@python3 setup.py sdist --dist-dir $(dist)/jinlava 

pypi:	~/.pypirc jinlava
	twine upload -r "$(pypi)" "dist/jinlava/jinlava-$(LAVA_VERSION).tar.gz"


# ------------------------------------------------------------------------------
# Documentation related targets
#
doc spell preview publish:
	$(MAKE) -C doc $(MAKECMDGOALS) dist=$(abspath $(dist))

# ------------------------------------------------------------------------------
tools:
	$(MAKE) -C dev-tools $(MAKECMDGOALS) dist=$(abspath $(dist))

black:
	black .
	black $(HIDDEN_PYTHON)

check:
	$(etc)/git-hooks/pre-commit


oracle:
	@mkdir -p external-packages/oracle
	@PATH=etc:$$PATH etc/oracle-pkg-sync.sh external-packages/oracle
	
endif

clean:
	$(RM) $(PKG) $(LIB_PKG)
	$(MAKE) -C doc $(MAKECMDGOALS) dist=$(abspath $(dist))
	$(MAKE) -C cfn $(MAKECMDGOALS) dist=$(abspath $(dist))
	$(MAKE) -C lambda $(MAKECMDGOALS) dist=$(abspath $(dist))

count:
	tokei .


# ------------------------------------------------------------------------------
#  Test targets

# Need to make sure we can access AWS or a lot of the tests will fail.
_aws:
	@aws sts get-caller-identity > /dev/null

ifeq ($(TESTS),yes)
coverage: _aws
	@mkdir -p dist/test
	pytest --cov=. --cov-report html:dist/test/htmlcov -n "$(PYTEST_WORKERS)"

test:	_aws
	pytest -v -s -n "$(PYTEST_WORKERS)"

start stop up down:
	$(MAKE) -C test $(MAKECMDGOALS)
else
coverage test start stop up down:
	@echo "Test targets are not enabled in this clone"
endif
