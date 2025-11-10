# ------------------------------------------------------------------------------
#  Common components for use in other makefiles.
# ------------------------------------------------------------------------------

# Local docker registry for builders. Avoid port 5000 on Big Sur

ifeq ($(repo_base),)
$(error repo_base not set)
endif

dist=$(repo_base)/dist
etc=$(repo_base)/etc

REGISTRY_LOCAL_PORT=5001


e=echo -e
# ANSI codes. Upper case are colours. Lower case, effects (italic etc.). _ is reset.
K=\033[30m
R=\033[31m
G=\033[32m
Y=\033[33m
B=\033[34m
M=\033[35m
C=\033[36m
W=\033[37m
# b(old), d(im), i(talic), u(nderline)
b=\033[1m
d=\033[2m
i=\033[3m
u=\033[4m
# Reset
_=\033[0m

# DO NOT delete this empty help target.
help:

# Start a local docker registry with local storage
registry:
	jindr start
	@$e "$GWhen done, stop local docker registry using \"jindr stop\"$_" ; \

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

# Build a multi-platform docker image that can build our lava package.
# This gets pushed to a local registry (required for multi-platform builds).
builder: _runtime registry
	@$e "$GBuilding/refreshing build images: build/lava/$(runtime)$_"
	docker buildx build --push --pull --force-rm \
		--platform=linux/amd64,linux/arm64 \
		-f $(etc)/builders/$(runtime).Dockerfile \
		-t localhost:$(REGISTRY_LOCAL_PORT)/build/lava/$(runtime) \
		--build-arg PIP_INDEX_URL="$$PIP_INDEX_URL" \
		$(etc)/builders
