# ------------------------------------------------------------------------------
# This makefile is used to build lava docker images.
#
# Try:
# 	make help
#
# ------------------------------------------------------------------------------

SHELL:=/bin/bash
repo_base=..

# These are set as labels on the images and annotations on the manifest.
IMAGE_DESCRIPTION=Lava is an AWS based distributed scheduler and job runner
define IMAGE_ATTRS
org.opencontainers.image.url=https://github.com/jin-gizmo/lava
org.opencontainers.image.source=https://github.com/jin-gizmo/lava
org.opencontainers.image.documentation=https://jin-gizmo.github.io/lava
org.opencontainers.image.licenses=BSD-3-Clause
endef
export IMAGE_ATTRS

include $(repo_base)/etc/Makefile

tag=latest

LAVA_VERSION=$(shell python3 ../lava/version.py)
LAVA_FULL_VERSION=$(shell python3 ../lava/version.py --all)

PKG=common/base/lava-$(LAVA_VERSION).tar.bz2
OS=$(shell cd os && find * -maxdepth 0 -type d)

platform=linux/amd64,linux/arm64

# Add --progress=plain if you need to see full build activity.
BUILD=docker buildx build --platform="$(platform)"
BUILD_DATE=$(shell date -u +%Y-%m-%dT%H:%M:%SZ)

# External registry
registry=ghcr.io
ifneq ($(registry),)
REGISTRY=$(registry:%/=%)/
endif

# Prior to the open source version (8.2), prefix was set to "dist". This made
# (some) sense within Origin, but none at all for the o/s version.
prefix=jin-gizmo
ecr-%: prefix=dist

# Repo prefix for the external registry
REPO_PREFIX=$(prefix:%/=%)/


.PHONY: help clean all base full package os pkg


# Cyan + italic
x=$C$i

# ------------------------------------------------------------------------------
help:
	@echo
	@$e "This makefile is used to build lava docker images. Many of the targets"
	@$e "accept (or require) $ikey=value$_ arguments. The default values are shown."
	@echo
	@$e "Available targets are:"
	@echo
	@$e "$RBuild related targets:$_"
	@$e "$x   build os=... [platform=$(platform)] [tag=$(tag)]$_"
	@$e "                 Make the base and full images for a specified O/S type."
	@$e "$x   build-all [platform=$(platform)] [tag=$(tag)]$_"
	@$e "                 Make the base and full images for all available O/S types."
	@$e "$x   base os=... [platform=$(platform)] [tag=$(tag)]$_"
	@$e "                 Make a lava image without CLI connector executables."
	@$e "$x   full os=... [platform=$(platform)] [tag=$(tag)]$_"
	@$e "                 Make a lava image with CLI connector executables."
	@$e "$x   check os=... [platform=$(platform)]$_"
	@$e "                 Perform a fast and flimsy check on the image."
	@$e "$x   check-all [platform=$(platform)]$_"
	@$e "                 Perform a fast and flimsy check on all images."
	@$e "$x   pkg$_           Make the lava code package for docker containers."
	@$e "$x   registry$_      Start a local docker registry to hold multi-plaftorm images."
	@$e "                 The registry is managed by the \"jindr\" utility. Try"
	@$e "                 \"jindr --help\" for more information."
	@echo
	@$e "$RAWS ECR related targets:$_"
	@$e "$x   ecr-repo os=... [prefix=dist]$_"
	@$e "                 Create ECR 'base' and 'full' repos for the specified O/S type."
	@$e "$x   ecr-push os=... [prefix=dist]$_"
	@$e "                 Push the 'base' and 'full' images to the ECR repo for the"
	@$e "                 specified O/S type."
	@$e "$x   ecr-repo-all [prefix=dist]$_"
	@$e "                 Create ECR repos for all images."
	@$e "$x   ecr-all [prefix=dist]$_"
	@$e "                 Push all images to the ECR repos."
	@echo
	@$e "$RDocker regisry related targets:$_"
	@$e "$x   push os=... [registry=$(registry)] [prefix=$(prefix)]$_"
	@$e "                 Copy the 'base' and 'full' images to the external registry"
	@$e "                 for the specified O/S type."
	@$e "$x   push-all [registry=$(registry)] [prefix=$(prefix)]$_"
	@$e "                 Push all images to the external registy."
	@echo
	@$e "$RMiscellaneous targets:$_"
	@$e "$x   clean$_         Remove the generated lava packages and docker junk."
	@$e "$x   help$_          Print this help text."
	@echo
	@$e "$RMake value arguments:$_"
	@$e "$x   os=...$_        Base O/S type: $(OS)"
	@$e "$x   platform=...$_  By default, multi-platform images will be built supporting"
	@$e "                 x86 (linux/amd64) and ARM (linux/arm64). This argument can"
	@$e "                 override that."
	@$e "$x   registry=...$_  Docker registry. Default is $(registry)."
	@$e "$x   prefix=...$_    Prefix for the exported image tag. Default is dist for ecr-*"
	@$e "                 targets and $(prefix) otherwise. The resulting image tag will"
	@$e "                 be something like $i<registry>/<prefix>/lava/<os>/...$_"
	@$e "$x   tag=...$_       Tag for the image. Default is latest."
	@echo

# ------------------------------------------------------------------------------

_FORCE:

$(PKG): _FORCE
	$(etc)/pkg.sh -f $(PKG) ..

pkg:	$(PKG)

build-all:
	@for os in $(OS) ; \
	do \
		$(MAKE) build os=$$os "tag=$(tag)" || exit 1 ; \
	done

ecr-repo-all:
	@for os in $(OS) ; \
	do \
		$(MAKE) ecr-repo os=$$os || exit 1 ; \
	done

ecr-all: check-all
	@for os in $(OS) ; \
	do \
		$(MAKE) ecr-push os=$$os || exit 1 ; \
	done

push-all: check-all
	@for os in $(OS) ; \
	do \
		$(MAKE) push os=$$os || exit 1 ; \
	done

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

# Build base and full images for given O/S
build:
	@for i in base full ; \
	do \
		$e "$B======================================================================$_" ; \
		$e "$BBuilding $(os) $$i$_" ; \
		$e "$B======================================================================$_" ; \
		$(MAKE) $$i os=$(os) "tag=$(tag)" || exit 1 ; \
	done

# Build a version without CLI connector executables

base:	os Dockerfile $(PKG) registry
	@if [ ! -f "os/$(os)/from.txt" ]; then echo "os/$(os)/from.txt: No such file"; exit 1; else :; fi
	@echo lava version is $(LAVA_VERSION)
	( \
		set -e ; \
		DESCRIPTION="Base installation of lava, without external components required to use CLI based connectors." \
		TMP=$$(mktemp -d) ; \
		z=3 ; \
		trap '/bin/rm -rf $$TMP; exit $$z' 0 ; \
		cp -RL os/$(os)/$@/* $$TMP ; \
		cp -L $(PKG) $$TMP ; \
		ls -lR $$TMP ; \
		LABELS=() ; \
		while IFS= read -r line ; \
		do \
			LABELS+=("--label" "$$line" "--annotation" "index,manifest:$$line") ; \
		done <<< "$$IMAGE_ATTRS" ; \
		$(BUILD) --rm --push --pull --provenance=false \
			-t localhost:$(REGISTRY_LOCAL_PORT)/lava/$(os)/$@:$(tag) \
			-t localhost:$(REGISTRY_LOCAL_PORT)/lava/$(os)/$@:$(LAVA_VERSION) \
			--build-arg "version=$(LAVA_VERSION)" \
			--build-arg "base=$(shell cat os/$(os)/from.txt)" \
			--build-arg "type=$@" \
			--build-arg "os=$(os)" \
			--label org.opencontainers.image.title="Lava $@ ($(os))" \
			--label org.opencontainers.image.description="$$DESCRIPTION" \
			--annotation index,manifest:org.opencontainers.image.description="$$DESCRIPTION" \
			"$${LABELS[@]}" \
			-f Dockerfile $$TMP ; \
		z=0 ; \
	)

# Build a version with everything, including CLI connector executables
full:	os Dockerfile $(PKG) registry
	@echo lava version is $(LAVA_VERSION)
	( \
		set -e ; \
		DESCRIPTION="Full installation of lava, including external components required to use CLI based connectors." \
		TMP=$$(mktemp -d) ; \
		z=3 ; \
		trap '/bin/rm -rf $$TMP; exit $$z' 0 ; \
		cp -RL os/$(os)/$@/* $$TMP ; \
		mkdir -p $$TMP/packages ; \
		cp -RL packages $$TMP ; \
		ls -lR $$TMP ; \
		while IFS= read -r line ; \
		do \
			LABELS+=("--label" "$$line" "--annotation" "index,manifest:$$line") ; \
		done <<< "$$IMAGE_ATTRS" ; \
		$(BUILD) --rm --push --pull --provenance=false \
			-t localhost:$(REGISTRY_LOCAL_PORT)/lava/$(os)/$@:$(tag) \
			-t localhost:$(REGISTRY_LOCAL_PORT)/lava/$(os)/$@:$(LAVA_VERSION) \
			--build-arg "version=$(LAVA_VERSION)" \
			--build-arg "base=localhost:$(REGISTRY_LOCAL_PORT)/lava/$(os)/base:$(LAVA_VERSION)" \
			--build-arg "type=$@" \
			--build-arg "os=$(os)" \
			--label org.opencontainers.image.title="Lava $@ ($(os))" \
			--label org.opencontainers.image.description="$$DESCRIPTION" \
			--annotation index,manifest:org.opencontainers.image.description="$$DESCRIPTION" \
			"$${LABELS[@]}" \
			-f Dockerfile $$TMP ; \
		z=0 ; \
	)

# Create the ECR repo for the given OS type and apply lifecycle policy
ecr-repo:
	aws ecr create-repository --repository-name "$(REPO_PREFIX)lava/$(os)/base"
	aws ecr create-repository --repository-name "$(REPO_PREFIX)lava/$(os)/full"
	aws ecr put-lifecycle-policy --repository-name "$(REPO_PREFIX)lava/$(os)/base" \
		--lifecycle-policy-text file://lifecycle.json
	aws ecr put-lifecycle-policy --repository-name "$(REPO_PREFIX)lava/$(os)/full" \
		--lifecycle-policy-text file://lifecycle.json

# Copy the images from our local registry to ECR for the given OS type.
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


# Copy the images from our local registry to the remote registry for the given
# OS type. Must have logged in to the remote registry first.
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

# Run a very quick and dirty check
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

clean:
	$(RM) $(PKG)
	docker system prune -f

