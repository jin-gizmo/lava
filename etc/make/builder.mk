# ------------------------------------------------------------------------------
#  Makefile for building lava builder images
# ------------------------------------------------------------------------------

MAKEFILE_DIR := $(dir $(lastword $(MAKEFILE_LIST)))
include $(MAKEFILE_DIR)/const.mk
include $(MAKEFILE_DIR)/registry.mk

# Local docker registry for builders. Avoid port 5000 on Big Sur

ifeq ($(repo_base),)
$(error repo_base not set)
endif

dist=$(repo_base)/dist
etc=$(repo_base)/etc


# Job count for make -j operations when creating a builder
jobs=4

# ------------------------------------------------------------------------------

#:cat Build targets

## Build a multi-platform docker image that can build the lava worker install
## package for the specified *runtime* on foreign platforms. ARM (`linux/arm64`)
## and x86 (`linux/amd64`) are supported. The *jobs* argument sets the number of
## parallel **make** jobs when building. Reduce this if memory errors occur.
#:req runtime=...
#:opt jobs
builder: _runtime registry
	@$e "$GBuilding/refreshing build images: build/lava/$(runtime)$_"
	docker buildx build --push --pull --force-rm \
		--platform=linux/amd64,linux/arm64 \
		-f $(etc)/builders/$(runtime).Dockerfile \
		-t localhost:$(REGISTRY_LOCAL_PORT)/build/lava/$(runtime) \
		--build-arg PIP_INDEX_URL="$$PIP_INDEX_URL" \
		--build-arg jobs="$(jobs)" \
		$(etc)/builders

# ------------------------------------------------------------------------------
# Check that a runtime has an available dockerfile
_runtime:
	@( \
		if [ ! -f "$(etc)/builders/$(runtime).Dockerfile" ] ; \
		then \
			echo "No builder Dockerfile for runtime $(runtime)" ; \
			exit 1 ; \
		else \
			: ; \
		fi ; \
	)
