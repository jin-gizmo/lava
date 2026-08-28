# ------------------------------------------------------------------------------
# This makefile is used to build lava docker images.
#
# Try:
# 	make help
#
# ------------------------------------------------------------------------------

SHELL:=/bin/bash
repo_base=..

include $(repo_base)/etc/make/common.mk
include $(repo_base)/etc/make/registry.mk
include $(repo_base)/etc/make/help.mk


# ------------------------------------------------------------------------------
# Auto-help setup
#
#+ This makefile is used to build lava docker images. Images come in *base* and
#+ *full* variants for various target operating systems. Multiplatform images
#+ are created by default.

#- For more information, consult the lava user guide $(_URL)

HELP_CATEGORY=Miscellaneous targets

# Force category ordering
#:cat Build targets
#:cat AWS ECR targets
#:cat Docker registry targets
#:cat Miscellaneous targets


# ------------------------------------------------------------------------------

# These are set as labels on the images and annotations on the manifest.
IMAGE_DESCRIPTION=Lava is an AWS based distributed scheduler and job runner
define IMAGE_ATTRS
org.opencontainers.image.url=https://github.com/jin-gizmo/lava
org.opencontainers.image.source=https://github.com/jin-gizmo/lava
org.opencontainers.image.documentation=https://jin-gizmo.github.io/lava
org.opencontainers.image.licenses=BSD-3-Clause
endef
export IMAGE_ATTRS

## Tag for built images.
tag=latest

LAVA_VERSION=$(shell python3 ../lava/version.py)
LAVA_FULL_VERSION=$(shell python3 ../lava/version.py --all)

PKG=common/base/lava-$(LAVA_VERSION).tar.bz2
OS:=$(shell cd os && find * -maxdepth 0 -type d)
_OS:=$(foreach x,$(OS), `$x`)
## Base O/S type: $(_OS)
os=

## By default, multi-platform images will be built supporting x86
## (`linux/amd64`) and ARM (`linux/arm64`). This variable can override that.
platform=linux/amd64,linux/arm64
COMMA=,
ifeq (,$(findstring $(COMMA),$(platform)))
    # Can't have index annotations in single platform build
    ANNOTATIONS=manifest
else
    ANNOTATIONS=index,manifest
endif

## Docker build progress information style. Set to `plain` to see full build activity.
progress=auto
BUILD=docker buildx build --platform="$(platform)" --progress="$(progress)"
BUILD_DATE=$(shell date -u +%Y-%m-%dT%H:%M:%SZ)

## Target docker registry for published images.
registry=ghcr.io
ifneq ($(registry),)
REGISTRY=$(registry:%/=%)/
endif

## Prefix for the exported image tag. Default is dist for `ecr-*` targets and
## `$(prefix)` otherwise. The resulting image tag will be something like
## `<registry>/<prefix>/lava/<os>/...`.
prefix=jin-gizmo
ecr-%: prefix=dist

# Repo prefix for the external registry
REPO_PREFIX=$(prefix:%/=%)/


.PHONY: help clean all base full package os pkg

# ------------------------------------------------------------------------------

_FORCE:

$(PKG): _FORCE
	$(etc)/pkg.sh -f $(PKG) ..

pkg:	$(PKG)

#:cat Build targets
## Make the *base* and *full* images for all available O/S types.
#:opt platform tag progress
build-all:
	@for os in $(OS) ; \
	do \
		$(MAKE) build os=$$os "tag=$(tag)" || exit 1 ; \
	done

#:cat AWS ECR targets

## Create ECR repos for all images.
#:opt prefix=dist
ecr-repo-all:
	@for os in $(OS) ; \
	do \
		$(MAKE) ecr-repo os=$$os || exit 1 ; \
	done

## Push all images from the local registry to the ECR repos.
#:opt prefix=dist
ecr-all: check-all
	@for os in $(OS) ; \
	do \
		$(MAKE) ecr-push os=$$os || exit 1 ; \
	done

#:cat Docker registry targets
## Push all images from the local registry to the external registry.
#:opt registry prefix
push-all: check-all
	@for os in $(OS) ; \
	do \
		$(MAKE) push os=$$os || exit 1 ; \
	done

#:cat Build targets
## Perform a fast and flimsy check on all images.
#:opt platform
check-all:
	@for os in $(OS) ; \
	do \
		$(MAKE) check os=$$os || exit 1 ; \
	done

ifdef os

os:
	@if [ ! -d os/$(os) ] ; \
	then \
		echo "$(os): unknown OS type for docker base image" >&2 ; \
		exit 1 ; \
	fi

# ------------------------------------------------------------------------------
#:cat Build targets

## Build the *base* and *full* lava images for a specified O/S type.
#:req os
#:opt platform tag progress
build:
	@for i in base full ; \
	do \
		$e "$B======================================================================$_" ; \
		$e "$BBuilding $(os) $$i$_" ; \
		$e "$B======================================================================$_" ; \
		$(MAKE) $$i os=$(os) "tag=$(tag)" || exit 1 ; \
	done

## Build a lava image without CLI connector executables.
#:req os
#:opt platform tag progress
base:	os Dockerfile $(PKG) registry
	@if [ ! -f "os/$(os)/from.txt" ]; then echo "os/$(os)/from.txt: No such file"; exit 1; else :; fi
	@echo lava version is $(LAVA_VERSION)
	( \
		set -e ; \
		description="Base installation of lava, without external components required to use CLI based connectors." \
		tmp=$$(mktemp -d) ; \
		z=3 ; \
		trap '/bin/rm -rf $$tmp; exit $$z' 0 ; \
		cp -RL os/$(os)/$@/* $$tmp ; \
		cp -L $(PKG) $$tmp ; \
		ls -lR $$tmp ; \
		LABELS=() ; \
		while IFS= read -r line ; \
		do \
			LABELS+=("--label" "$$line" "--annotation" "$(ANNOTATIONS):$$line") ; \
		done <<< "$$IMAGE_ATTRS" ; \
		$(BUILD) --rm --push --pull --provenance=false \
			-t localhost:$(REGISTRY_LOCAL_PORT)/lava/$(os)/$@:$(tag) \
			-t localhost:$(REGISTRY_LOCAL_PORT)/lava/$(os)/$@:$(LAVA_VERSION) \
			--build-arg "version=$(LAVA_VERSION)" \
			--build-arg "base=$(shell cat os/$(os)/from.txt)" \
			--build-arg "type=$@" \
			--build-arg "os=$(os)" \
			--label org.opencontainers.image.title="Lava $@ ($(os))" \
			--label org.opencontainers.image.description="$$description" \
			--annotation "$(ANNOTATIONS):org.opencontainers.image.description"="$$description" \
			"$${LABELS[@]}" \
			-f Dockerfile $$tmp ; \
		z=0 ; \
	)

## Make a lava image with everything, including CLI connector executables.
#:req os
#:opt platform tag progress
full:	os Dockerfile $(PKG) registry
	@echo lava version is $(LAVA_VERSION)
	( \
		set -e ; \
		description="Full installation of lava, including external components required to use CLI based connectors." \
		tmp=$$(mktemp -d) ; \
		z=3 ; \
		trap '/bin/rm -rf $$tmp; exit $$z' 0 ; \
		cp -RL os/$(os)/$@/* $$tmp ; \
		mkdir -p $$tmp/packages ; \
		cp -RL packages $$tmp ; \
		ls -lR $$tmp ; \
		while IFS= read -r line ; \
		do \
			LABELS+=("--label" "$$line" "--annotation" "$(ANNOTATIONS):$$line") ; \
		done <<< "$$IMAGE_ATTRS" ; \
		$(BUILD) --rm --push --pull --provenance=false \
			-t localhost:$(REGISTRY_LOCAL_PORT)/lava/$(os)/$@:$(tag) \
			-t localhost:$(REGISTRY_LOCAL_PORT)/lava/$(os)/$@:$(LAVA_VERSION) \
			--build-arg "version=$(LAVA_VERSION)" \
			--build-arg "base=localhost:$(REGISTRY_LOCAL_PORT)/lava/$(os)/base:$(LAVA_VERSION)" \
			--build-arg "type=$@" \
			--build-arg "os=$(os)" \
			--label org.opencontainers.image.title="Lava $@ ($(os))" \
			--label org.opencontainers.image.description="$$description" \
			--annotation "$(ANNOTATIONS):org.opencontainers.image.description"="$$description" \
			"$${LABELS[@]}" \
			-f Dockerfile $$tmp ; \
		z=0 ; \
	)

# ------------------------------------------------------------------------------
#:cat AWS ECR targets

## Create ECR *base* and *full* repos for the specified O/S type.
## A lifecycle policy will also be added.
#:req os
#:opt prefix=dist
ecr-repo:
	aws ecr create-repository --repository-name "$(REPO_PREFIX)lava/$(os)/base"
	aws ecr create-repository --repository-name "$(REPO_PREFIX)lava/$(os)/full"
	aws ecr put-lifecycle-policy --repository-name "$(REPO_PREFIX)lava/$(os)/base" \
		--lifecycle-policy-text file://lifecycle.json
	aws ecr put-lifecycle-policy --repository-name "$(REPO_PREFIX)lava/$(os)/full" \
		--lifecycle-policy-text file://lifecycle.json

## Push the *base* and *full* images from the local registry to the ECR repo for
## the specified O/S type.
#:req os
#:opt prefix=dist
ecr-push: registry
	@( \
		set -e ; \
		$(repo_base)/etc/ecr-login ; \
		for type in base full : \
		do \
			repo="$(REPO_PREFIX)lava/amzn2023/$$type" ; \
			repo_uri=$$( \
				aws ecr describe-repositories --repository-names $$repo \
					--query 'repositories[0].repositoryUri' --output text \
				) ; \
			echo -e "$MUploading to $$repo_uri$_" ; \
			docker buildx imagetools create \
				--tag "$$repo_uri:latest" \
				--tag "$$repo_uri:$(LAVA_VERSION)" \
				"localhost:$(REGISTRY_LOCAL_PORT)/lava/$(os)/$$type:$(LAVA_VERSION)" ; \
		done ; \
	)


# ------------------------------------------------------------------------------
#:cat Docker registry targets

## Copy the *base* and *full* images from our local registry to the remote
## registry for the given OS type. **Log in to the remote registry first.**
#:req os
#:opt registry prefix
push:	registry
	@( \
		set -e ; \
		for type in base full ; \
		do \
			echo -e "$MPushing to $(REGISTRY)$(REPO_PREFIX)lava/$(os)/$$type$_" ; \
			docker buildx imagetools create \
				--tag "$(REGISTRY)$(REPO_PREFIX)lava/$(os)/$$type:latest" \
				"localhost:$(REGISTRY_LOCAL_PORT)/lava/$(os)/$$type:$(LAVA_VERSION)" ; \
			docker buildx imagetools create \
				--tag "$(REGISTRY)$(REPO_PREFIX)lava/$(os)/$$type:$(LAVA_VERSION)" \
				"localhost:$(REGISTRY_LOCAL_PORT)/lava/$(os)/$$type:$(LAVA_VERSION)" ; \
		done ; \
	)

#:cat Build targets
## Perform a fast and flimsy check on the *base* and *full* images.
#:req os
#:opt platform
check:
	@IFS=',' read -r -a platforms <<< "$(platform)" ; \
	for p in "$${platforms[@]}" ; \
	do \
		for i in base full ; \
		do \
			echo -e "$MChecking localhost:$(REGISTRY_LOCAL_PORT)/lava/$$os/$$i ($$p)$_" ; \
			common/img-check.sh -p "$$p" localhost:$(REGISTRY_LOCAL_PORT)/lava/$$os/$$i || exit 1 ; \
		done ; \
	done
	

else

base full ecr-repo ecr-push check push:
	$(error The os parameter must be specified)
endif

## Remove the generated lava packages and docker junk.
#:cat Miscellaneous targets
clean:
	$(RM) $(PKG)
	docker system prune -f

