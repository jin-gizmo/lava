# Generic makefile. This is imported into the other makefiles rather than being
# invoked here. Requires the bin directory for the project to be in the path.

SHELL:=/bin/bash

ifndef env
$(error env must be defined. Try make $(MAKECMDGOALS) env=...)
endif

ifndef BASEDIR
BASEDIR=..
endif
ETC=$(BASEDIR)/etc

ifndef CONFIG
CONFIG=$(BASEDIR)/config/$(env).yaml
endif

ifndef DIST
DIST=$(BASEDIR)/dist/$(env)/$(shell basename `pwd`)
endif

override REALM_INFO=$(BASEDIR)/dist/$(env)/.realm.json

NOW_TZ=$(shell python -c "import datetime, dateutil.tz; print(datetime.datetime.now(dateutil.tz.tzlocal()).replace(microsecond=0).isoformat())")

# DOCKER_PLATFORM is only used if a value is not specified in the config file.
# Previous framework versions had no notion of platform and the base images were 
# typically x86 so we set the default platform version to continue that combo to
# minimise migration issues. At some point this should be changed to
# linux/amd64,linux/arm64 to build multi-platform images by default but that will
# require some change to the build process to build and push in one go.
DOCKER_PLATFORM=linux/amd64

ifeq ($(xattr),no)
X_LAVA_VARS=
else

GIT_BRANCH=$(shell git status -bs 2>/dev/null | sed -e 's/^\#\# //' -e 1q)
ifeq ($(GIT_BRANCH),)
GIT_BRANCH=--
endif

GIT_REPO=$(shell git config --get remote.origin.url)
ifeq ($(GIT_REPO),)
GIT_REPO=--
endif


CHECKSUM_KEY_NAME=x-lava-chk
CHECKSUM_HASH_ALGORITHM=sha256

X_LAVA_VARS=\
	-p x-lava-built="$(NOW_TZ)" \
	-p x-lava-builder="Lava Framework $(shell cat $(ETC)/version)" \
	-p x-lava-os="$(shell os-type)" \
	-p x-lava-host="$(shell hostname)" \
	-p x-lava-git-branch="$(GIT_BRANCH)" \
	-p x-lava-git-repo="$(GIT_REPO)" \
	-p x-lava-git-status="$(shell git-commit-info)" \
	-p x-lava-user="$(shell whoami)"
endif

# ------------------------------------------------------------------------------
# Define some useful functions

#  Deploy lava objects in DynamoDB specs
#  Usage: $(call lava_put_job,realm,json-file...)
#         json-file can be a space separated list
lava_put_job=dyn-put-item --table lava.$(1).jobs $(2)
lava_put_conn=dyn-put-item --table lava.$(1).connections $(2)
lava_put_trigger=dyn-put-item --table lava.$(1).s3triggers $(2)

# Extract a value from the config file or the realm info file.
# Usage: $(call get_config,var-name)
get_config=$(shell echo '+{$(1)}+' | jinja -d+ --file '$(CONFIG)' --file '$(REALM_INFO)')

# Extract a value from the realm info
# Usage: $(call get_realm_info,var-name)
get_realm_info=$(shell echo '+{$(1)}+' | jinja -d+ --file '$(REALM_INFO)')

# Find files with a name matching pattern. Any top level directories starting
# with _ (i.e. underscore) are ignored. Any leading ./ is stripped from the
# output of find.
# Usage: $(call find_by_name,pattern)
#        pattern is a glob pattern, e.g. "*.yaml"
find_by_name=$(shell find -L . ! -path "*/_*" -name "$1" | sed "s|^\./||")

# ------------------------------------------------------------------------------
# Some generic rules

FORCE:

$(DIST):
	@mkdir -p $(DIST)

# . . . . . . . . . . . . . . . . . . . .
# Render JSON files into dist dir
$(DIST)/%.json: %.json $(CONFIG)
	@mkdir -p $(@D)
	@echo "Build  $@"
	@( \
		set -o pipefail ; \
		jinja --delimiter \< --file $(CONFIG) --file $(REALM_INFO) -p env="$(env)" $*.json | \
			json-inject \
				--hash-name "$(CHECKSUM_KEY_NAME)" \
				--hash-algorithm "$(CHECKSUM_HASH_ALGORITHM)" \
				--hash-ignore "[xX]-*" \
				--hash-tag FW \
				$(X_LAVA_VARS)  > $@ ; \
		if [ $$? -ne 0 ] ; \
		then \
			$(RM) $@ ; \
			exit 1 ; \
		else \
			true ; \
		fi ; \
	)

# . . . . . . . . . . . . . . . . . . . .
# Render sql files into dist dir
$(DIST)/%.sql: %.sql $(CONFIG)
	@mkdir -p $(@D)
	@echo "Build  $@"
	@jinja --delimiter \< --file $(CONFIG) --file $(REALM_INFO) -p env="$(env)" $*.sql > $@

# . . . . . . . . . . . . . . . . . . . .
# Render YAML files into dist dir
$(DIST)/%.json: %.yaml $(CONFIG)
	@mkdir -p $(@D)
	@echo "Build  $@"
	@( \
		set -o pipefail ; \
		jinja --delimiter \< --file $(CONFIG) --file $(REALM_INFO) -p env="$(env)" $*.yaml | \
			yaml2json | \
			json-inject \
				--hash-name "$(CHECKSUM_KEY_NAME)" \
				--hash-algorithm "$(CHECKSUM_HASH_ALGORITHM)" \
				--hash-ignore "[xX]-*" \
				--hash-tag FW \
				$(X_LAVA_VARS)  > $@ ; \
		if [ $$? -ne 0 ] ; \
		then \
			$(RM) $@ ; \
			exit 1 ; \
		else \
			true ; \
		fi ; \
	)

# . . . . . . . . . . . . . . . . . . . .
# Simple copy of Python files into dist payloads
$(DIST)/%.py: %.py $(CONFIG)
	@mkdir -p $(@D)
	@echo "Build  $@"
	cp $*.py $@

# . . . . . . . . . . . . . . . . . . . .
# Simple copy of shell scripts into dist payloads
$(DIST)/%.sh: %.sh $(CONFIG)
	@mkdir -p $(@D)
	@echo "Build  $@"
	cp $*.sh $@

# . . . . . . . . . . . . . . . . . . . .
# Convert Jupyter notebook to Python
$(DIST)/%.py: %.ipynb $(CONFIG)
	@mkdir -p $(@D)
	@echo "Build  $@"
	@ipynb2py -T $(ETC)/sagemakertopython.tpl --output-dir $(@D) $*.ipynb

# . . . . . . . . . . . . . . . . . . . .
%.json:	%.yaml $(CONFIG)
	yaml2json < $*.yaml > $@

# . . . . . . . . . . . . . . . . . . . .
# Zip up code bundles for pkg jobs.
# Requires dynamic make to pick up all changes in pkg dir.

$(DIST)/%.zip: FORCE
	@mkdir -p $(@D)
	@( \
		echo '$@: $(CONFIG) $$(shell find -L $*.pkg)' ; \
		echo '	lava-pkg -c $(CONFIG) -p env="$(env)" -T $(ETC)/sagemakertopython.tpl $*.pkg $@' ; \
	) | $(MAKE) -f /dev/stdin

# . . . . . . . . . . . . . . . . . . . . 
# Build for docker jobs. The target is a file containing the image ID.
# Requires dynamic make to pick up all changes in pkg dir.

$(DIST)/%.dockerimg: FORCE
	@mkdir -p $(@D)
	$(eval docker_pfx=$(shell echo '+{prefix.docker_repo}+' | jinja -d + --file $(CONFIG) --file $(REALM_INFO)))
	$(eval base_img=$(shell echo '+{docker.base_img}+' | jinja -d + --file $(CONFIG) --file $(REALM_INFO)))
	$(eval platform=$(shell echo '+{docker.platform or "$(DOCKER_PLATFORM)"}+' | jinja -d + --file $(CONFIG) --file $(REALM_INFO)))
	@( \
		echo '$@: $(CONFIG) $$(shell find -L $*.docker)' ; \
		echo '	lava-docker -c $(CONFIG) -p env="$(env)" -P "$(platform)" -b PIP_INDEX_URL -b BASE_IMG="$(base_img)" -t $(docker_pfx)/$* -T $(ETC)/sagemakertopython.tpl -i $@ $*.docker $(ETC)/Dockerfile' ; \
	) | $(MAKE) -f /dev/stdin

# . . . . . . . . . . . . . . . . . . . . 
# Build for resource dirs. The target is a directory containing a
# Jinja renderred version of all the source files

$(DIST)/%.rsc: FORCE
	@mkdir -p $(@D)
	@( \
		echo '$@: $(CONFIG) $$(shell find -L $*.rsc)' ; \
		echo '	$$(RM) -r $@' ; \
		echo '	lava-rsc -L -c $(CONFIG) -p env="$(env)" $*.rsc $@' ; \
	) | $(MAKE) -f /dev/stdin

# Raw dirs are copied as is.
$(DIST)/%.raw: FORCE
	@mkdir -p $(@D)
	@( \
		echo '$@: $(CONFIG) $$(shell find -L $*.raw)' ; \
		echo '	$$(RM) -r $@' ; \
		echo '	cp -LR $*.raw $@' ; \
	) | $(MAKE) -f /dev/stdin
