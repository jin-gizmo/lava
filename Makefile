# ex: cc=80,95

SHELL:=/bin/bash

repo_base=.
REPO_URL=https://github.com/jin-gizmo/lava

include $(repo_base)/etc/make/common.mk
include $(repo_base)/etc/make/builder.mk
include $(repo_base)/etc/make/help.mk

# ------------------------------------------------------------------------------
# Auto-help setup
#
#+ Welcome to **$(APP) v$(LAVA_VERSION_ALL)**. What do you want to make?

#- For more information, consult the lava user guide $(_URL)
#-
#- Help brought to you by **MakeHelp** - https://github.com/jin-gizmo/makehelp.

HELP_CATEGORY=Getting started

# ------------------------------------------------------------------------------

APP=lava

# Too many workers actually slows it down.
PYTEST_WORKERS=auto
# PYTEST_WORKERS=2

# The name of an index server for twine uploads in `~/.pypirc`.
pypi=pypi

export LAVA_VERSION:=$(shell python3 lava/version.py)
LAVA_VERSION_ALL:=$(shell python3 lava/version.py --all)

# ------------------------------------------------------------------------------

override OS:=$(shell $(etc)/os-type.sh)
override PY_VER=$(shell python3 -c 'from sys import version_info as v; print(f"{v.major}.{v.minor}")')
override ARCH=$(shell arch)
override RUNTIME:=$(OS)-py$(PY_VER)

## Some targets need *runtime* to be specified to indicate the target O/S type
## and Python version (`$(runtime)` on this machine).  Building for a foreign
## runtime is done in a docker container. See `etc/builders` for Dockerfiles.

runtime:=$(RUNTIME)


## Some docker related targets need *platform* to be specified using standard
## docker nomenclature. e.g. `linux/arm64` (ARM), `linux/amd64` (x86).
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

# WHen doing "make release" to create a GitHub release default is ...
draft=no


ifneq ($(wildcard test/*),)
TESTS=yes
else
TESTS=no
endif

.PHONY: help deploy doc clean pkg jinlava lambda init upgrade spell test cfn oracle schemas

# ------------------------------------------------------------------------------
# This is a somewhat arbitrary subset of useful stuff. If what you need is not
# here, just build it yourself.
#


RELEASE_FILES=\
	$(wildcard dist/cfn/*.cfn.json) \
	dist/dev-tools/lava-job-framework-$(LAVA_VERSION).zip
	# $(wildcard dist/lambda/*-$(LAVA_VERSION).zip) \
	# dist/pkg/amzn2023/lava-$(LAVA_VERSION)-amzn2023-py3.11-aarch64.tar.bz2 \
	# dist/pkg/amzn2023/lava-$(LAVA_VERSION)-amzn2023-py3.11-x86_64.tar.bz2
	# dist/pkg/amzn2023/lava-$(LAVA_VERSION)-amzn2023-py3.13-aarch64.tar.bz2 \
	# dist/pkg/amzn2023/lava-$(LAVA_VERSION)-amzn2023-py3.13-x86_64.tar.bz2 \
	# dist/pkg/amzn2023/lava-$(LAVA_VERSION)-amzn2023-py3.14-aarch64.tar.bz2 \
	# dist/pkg/amzn2023/lava-$(LAVA_VERSION)-amzn2023-py3.14-x86_64.tar.bz2


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


# ------------------------------------------------------------------------------
#:cat Getting started

## Initialise the project (create venv etc.). This is non-destructive and can be
## rerun as needed.
init:	_venv req _git
	$(MAKE) -C test init

_git:	.git
	git config core.hooksPath etc/git-hooks

## Download / update the Oracle client binaries.
oracle:	_venv_is_on
	@mkdir -p external-packages/oracle
	@PATH=etc:$$PATH etc/oracle-pkg-sync.sh external-packages/oracle

## Check software prequisites.
req:	_venv
	@echo "🔵 Checking prerequisites"
	@( \
		source venv/bin/activate ; \
		req install --optional req.yaml ; \
	)

# ------------------------------------------------------------------------------
#:cat Build targets

## Build the lava worker install package. If the target *runtime* does not match
## the current one (`$(runtime)`), the build will be done in a docker container
## based on a *builder* image.
#:opt runtime platform
pkg:	freeze _pkg

## Build the CloudFormation templates and associated documentation.
cfn:	_venv_is_on
	$(MAKE) -C cfn cfn dist=$(abspath $(dist))

## Build the lambda function code bundles.
lambda: _venv_is_on
	$(MAKE) -C lambda lambda dist=$(abspath $(dist))

## Create a source distribution of the lava Python package for installation
## using **pip**.
jinlava: $(LIB_PKG)


## Build the JSON schema files.
schemas: _venv_is_on \
	$(patsubst schemas/%.schema.yaml,dist/schemas/%.schema.yaml,$(wildcard schemas/*.schema.yaml)) \
	$(patsubst schemas/%.schema.yaml,dist/schemas/%.schema.json,$(wildcard schemas/*.schema.yaml))


.SECONDEXPANSION:

$(dist)/schemas/%.schema.yaml: schemas/%.schema.yaml \
		$(shell find schemas/common -name '*.yaml') \
		$$(shell find schemas/$$* -name '*.yaml')
	@echo Buiding $@
	@mkdir -p $(dist)/schemas
	@( \
		set -e ; \
		components=(-d schemas/common) ; \
		[ -d "schemas/$*" ] && \
			components+=(-d "schemas/$*") ; \
		etc/schema-build \
			"$${components[@]}" \
			-p "id=$(LAVA_DOCO_URL)/schemas/latest/$*.schema.yaml" \
			-p "documentation=$(LAVA_DOCO_URL)" \
			-p "version=v$(LAVA_VERSION)" \
			"$<" \
			> "$@" ; \
	)

$(dist)/schemas/%.schema.json: $(dist)/schemas/%.schema.yaml
	etc/schema2json < $< > $@

## Build the lava job framework.
tools:
	$(MAKE) -C dev-tools tools dist=$(abspath $(dist))


$(LIB_PKG): _venv_is_on $(SOURCE_FILES)
	@mkdir -p $(dist)/jinlava
	@python3 setup.py sdist --dist-dir $(dist)/jinlava 

_pkg:	$(PKG)

# If target O/S matches current, do a local build. Otherwise try to build in
# a container. See $(etc)/builders for dockerfiles for supported O/S.
# Note that we set PIP_INDEX_URL env var in the build to mimic pip behavour on
# the current host.

$(PKG):	_venv_is_on $(SOURCE_FILES)
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
			-e VIRTUAL_ENV=anything \
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
# Release related targets. These are really just shortcuts for commonly built
# artefacts and will evolve over time as things such as Python version support
# changes. We define these as targets rather than a variable listing targets
# because some of them require parameters in the build process.

RELEASE_RUNTIMES=amzn2023-py3.11 amzn2023-py3.13 amzn2023-py3.14
RELEASE_PLATFORMS=linux/arm64 linux/amd64

_release.builders:
	for r in $(RELEASE_RUNTIMES) ; \
	do \
		$(MAKE) builder runtime="$$r" ; \
	done

_release.pkg:	_release.builders
	$(MAKE) pkg
	for r in $(RELEASE_RUNTIMES) ; \
	do \
		for p in $(RELEASE_PLATFORMS) ; \
		do \
			$(MAKE) pkg runtime="$$r" platform="$$p" ; \
		done ; \
	done

_release.other: cfn jinlava lambda schemas tools

## Build a bunch of release related targets. This is essentially a shortcut for
## commonly built artefacts (excluding docker images).
##
## The *jobs* argument sets the number of parallel **make** jobs when building.
## Reduce this if memory errors occur.
## If `force` is set to `yes`, the builder images will be rebuilt, even if they
## already exist. By default, the builder images are not rebuilt if they already
## exist.
#:opt jobs force

artefacts: _release.pkg _release.other

artifacts:
	$(error Learn to spell dude ... the correct form is "artefacts" from the Latin "arte factum")

# ------------------------------------------------------------------------------
#:cat Installation targets

## Deploy modified files to S3. The *env* argument specifies a target
## environment configuration in `$(config)`. The optional *config* argument
## can specify a different config file.
#:req env
#:opt config

ifndef env
deploy:
	$(error You must specify env=... argument!)
else
deploy:
	$(etc)/deploy.sh -e $(env) -f $(config)
endif

## Upload the jinlava package to the `$(pypi)` PyPI server via twine. The
## `$(pypi)` server must be defined in `~/.pypirc`. Use the *pypi* argument to
## specify a different index server entry in `~/.pypirc`.
#:opt pypi
pypi:	~/.pypirc jinlava
	twine upload -r "$(pypi)" "dist/jinlava/jinlava-$(LAVA_VERSION).tar.gz"

retag=no

## Create a GitHub release containing selected generic assets. Set *draft* to
## either `yes` or `no`. To force updating an existing full version tag, set
## *retag* to `yes`.
#:opt draft retag

release: _repo_is_clean _on_master
	@( \
		case "$(retag)" \
		in \
			yes | true) force=-f ;; \
			no | false) force= ;; \
			*)	echo "Bad value for retag: $(retag) - must be yes or no" ; exit 1 ;; \
		esac ; \
		git tag $$force "v$(LAVA_VERSION)" ; \
		git push origin $$force "v$(LAVA_VERSION)" ; \
	)
	@$e "$GCreating GitHub release ...$_"
	@( \
		case "$(draft)" \
		in \
			yes | true) draft=true ;; \
			no | false) draft=false ;; \
			*)	echo "Bad value for draft: $(draft) - must be yes or no" ; exit 1 ;; \
		esac ; \
		if gh release view "v$(LAVA_VERSION)" > /dev/null 2>&1 ; \
		then \
			$e "$GUpdating existing release for tag v$(LAVA_VERSION)$_" ; \
			gh release upload --clobber "v$(LAVA_VERSION)" $(RELEASE_FILES) ; \
			gh release edit \
				--draft="$$draft" \
				--verify-tag=false \
				--title "Version $(LAVA_VERSION_ALL)" \
				--notes "https://jin-gizmo.github.io/lava/" \
				"v$(LAVA_VERSION)" ; \
		else \
			$e "$GCreating new release for tag v$(LAVA_VERSION)$_" ; \
			gh release create \
				--draft="$$draft" \
				--verify-tag=false \
				--title "Version $(LAVA_VERSION_ALL)" \
				--notes "https://jin-gizmo.github.io/lava/" \
				"v$(LAVA_VERSION)" \
				$(RELEASE_FILES) ; \
		fi ; \
	)
	@gh release view "v$(LAVA_VERSION)"


# ------------------------------------------------------------------------------
#:cat Documentation targets

## Build the user guide into consolidated markdown.
doc:	_venv_is_on
	$(MAKE) -C doc doc dist=$(abspath $(dist))

## Spell check the user guide (requires **aspell**).
spell:
	$(MAKE) -C doc spell dist=$(abspath $(dist))

## Build and preview the mkdocs version of the user guide.
preview: _venv_is_on
	$(MAKE) -C doc preview dist=$(abspath $(dist))

## Publish the user guide to GitHub pages (must be on *master* branch).
publish: _venv_is_on
	$(MAKE) -C doc publish dist=$(abspath $(dist))

# ------------------------------------------------------------------------------
#:cat Miscellaneous targets

## Format the Python code using **black**.
black:	_venv_is_on
	black .
	black $(HIDDEN_PYTHON)

## Run the pre-commit code checks (**ruff**, **flake8** etc).
check:	_venv_is_on
	$(etc)/git-hooks/pre-commit

## Remove the generated packages and documents.
clean:
	$(RM) $(PKG) $(LIB_PKG)
	$(MAKE) -C doc clean dist=$(abspath $(dist))
	$(MAKE) -C cfn clean dist=$(abspath $(dist))
	$(MAKE) -C lambda clean dist=$(abspath $(dist))

## Count lines of source code (needs **tokei**).
count:
	tokei .

## Upgrade the virtual environment with the latest Python packages.
upgrade: _venv_is_on
	python3 -m pip install -r requirements-build.txt --upgrade
	python3 -m pip install -r requirements.in --upgrade
	python3 -m pip install -r requirements-extra.in --upgrade
	
## Build frozen `requirements-*.txt` files based on versions currently
## installed in the venv.
freeze:	_venv_is_on $(REQ_FILES)

## Update the TOC in `README.md`.
toc:
	@set -e ; \
	tmp=$$(mktemp) ; \
	z=1 ; \
	trap '/bin/rm -f $$tmp; exit $$z' 0 ; \
	etc/tocmark README.md > $$tmp || exit ; \
	if cmp -s README.md $$tmp ; \
	then \
		echo "README.md already up to date" ; \
	else \
		cp README.md README.md.bak ; \
		mv $$tmp README.md ; \
		echo "README.md TOC updated" ; \
	fi ; \
	z=0



# ------------------------------------------------------------------------------
#:cat Test targets

ifeq ($(TESTS),yes)
## Run the unit tests and produce a coverage report.
coverage:

## Run the unit tests.
test:

## Load the test job suite into the ministack container
load:

## Start the docker containers providing test resources.
## The *services* parameter can be set to a comma separated list of service
## names to start only those. e.g. `services=ministack,mail`.
## See `docker-compose.yaml` for the available service names.
#:opt services
start:

## Check that the local docker based test infrastructure is ready to use (also
## included in the *test* and *coverage* targets).
## The *services* parameter can be set to a comma separated list of service
## names to start only those. e.g. `services=ministack,mail`.
## See `docker-compose.yaml` for the available service names.
#:opt services
ready:

## Stop the docker containers providing test resources.
stop:

## Update source images for test containers.
# Ministack, in particular, updates frequently (almost daily).
refresh:

start ready stop up down load test coverage refresh: _delegate
	@:

# This delegate nonsense is required to prevent stuff running twice when
# multiple targets are specified on the command line (e.g. make up load).
.PHONY: _delegate

_delegate:
	@$(MAKE) -C test $(MAKECMDGOALS)

else
start ready stop up down load test coverage refresh:
	@echo "Test targets are not enabled in this clone"
endif
