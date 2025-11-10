# Miscellaneous files. Files in this directory are not part of the lava job(s)
# per se but are related artefacts (e.g. SQL to create tables in databases).
#
# With the default configuration, all SQL scripts (*.sql) are Jinja rendered
# into the dist area.

include ../etc/Makefile

ifndef REALM
%:
	$(error Run make from the parent directory - not here)
endif

SRC_FILES=$(wildcard *.sql)

# There must be some kind of rule available to make everything in the
# DIST_FILES list. Default rules exist for:
# - SQL files that involve rendering
# - Standalone Python files that just need to be copied.
# - Standalone shell scripts that just need to be copied.
#
# For more complex bundles, add a custom rule to build the package
# into the $(DIST) directory.

DIST_FILES=$(foreach F,$(SRC_FILES),$(DIST)/$(F))

.PHONY: dist clean install _install uninstall


# Misc dir is a bit special - we let the user create their own rules
# for build and install related targers with a custom Makefile.

dist: $(DIST) $(DIST_FILES)

clean:
	$(RM) $(DIST_FILES)

ifeq (,$(wildcard Makefile.local))
# No Makefile.local - ignore other targets

%:
	@true

else
# We have Makefile.local

_install: dist install

uninstall: dist

diff:
	@echo Diff is not supported for misc

pre-install install uninstall dist:
	@echo "Running $@ in Makefile.local"
	@$(MAKE) -f Makefile.local $@

endif
