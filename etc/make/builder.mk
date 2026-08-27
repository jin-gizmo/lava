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

# If yes, force a builder docker image to be recreated even if it already exits.
force=no

# ------------------------------------------------------------------------------

#:cat Build targets

## Build a multi-platform docker image that can build the lava worker install
## package for the specified *runtime* on foreign platforms. ARM (`linux/arm64`)
## and x86 (`linux/amd64`) are supported.
##
## The *jobs* argument sets the number of parallel **make** jobs when building.
## Reduce this if memory errors occur.  If `force` is set to `yes`, the image
## will be rebuilt even if it already exists. By default, the image is not
## rebuilt if it already exists.
#:req runtime=...
#:opt jobs force
builder: _runtime registry
	@img="localhost:$(REGISTRY_LOCAL_PORT)/build/lava/$(runtime)" ; \
	if [[ "$(force)" != y* ]] && jindr lsi "$$img" > /dev/null 2>&1 ; \
	then \
		$e "$G$$img already exists -- use \"force=yes\" to rebuild$_" ; \
		exit 0 ; \
	else \
		$e "$GBuilding/refreshing build image: $$img$_" ; \
		docker buildx build --push --pull --force-rm \
			--platform=linux/amd64,linux/arm64 \
			-f $(etc)/builders/$(runtime).Dockerfile \
			-t localhost:$(REGISTRY_LOCAL_PORT)/build/lava/$(runtime) \
			--build-arg PIP_INDEX_URL="$$PIP_INDEX_URL" \
			--build-arg jobs="$(jobs)" \
			$(etc)/builders ; \
	fi

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
