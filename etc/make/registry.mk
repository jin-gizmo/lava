# ------------------------------------------------------------------------------
#  Makefile for building lava builder images
# ------------------------------------------------------------------------------

MAKEFILE_DIR := $(dir $(lastword $(MAKEFILE_LIST)))
include $(MAKEFILE_DIR)/const.mk

ifeq ($(repo_base),)
$(error repo_base not set)
endif

dist=$(repo_base)/dist
etc=$(repo_base)/etc

# ------------------------------------------------------------------------------
## Start a local docker registry to hold multi-plaftorm images. The registry is
## managed by the **jindr** utility.  Try *jindr --help* for more information.
#:cat Miscellaneous targets
registry:
	jindr -r "localhost:$(REGISTRY_LOCAL_PORT)" start
	@$e "$GWhen done, stop local docker registry using \"jindr stop\"$_" ; \

