# ------------------------------------------------------------------------------
#  etc/Makefile is no longer used. Use etc/make/common.mk instead.
# ------------------------------------------------------------------------------

# Drop the last file from the list because it's this file.
INCLUDED_BY := $(wordlist 1,$(shell echo $$(($(words $(MAKEFILE_LIST)) - 1))),$(MAKEFILE_LIST))
THIS_FILE := $(lastword $(MAKEFILE_LIST))

define NL


endef

define ERROR
[31m

--------------------------------------------------------------------------------
$(THIS_FILE) has been included by at least one of the files in this list:

 $(foreach w,$(INCLUDED_BY),$(w)$(NL))
This configuration is no longer supported. Replace the "etc/Makefile" part of the
include with "etc/make/common.mk".
--------------------------------------------------------------------------------
[0m
endef

$(error $(ERROR))
