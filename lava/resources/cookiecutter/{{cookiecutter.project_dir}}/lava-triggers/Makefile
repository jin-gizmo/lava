# # Create Lava s3trigger specifications. The specifications can be in YAML
# (preferred) or JSON.
#
# With the default configuration below all *.yaml and *.json files will be
# Jinja rendered one for one into the dist area with YAML files converted to
# JSON on the way. This is probably ok for most situations.
#
# NOTE:	The Jinja rendering uses non-standard Jinja delimiters to avoid
# 	conflict with normal Jinja syntax used by Lava. See README.md.

include ../etc/Makefile

ifndef REALM

%:
	$(error Run make from the parent directory - not here)

else

# List of files to generate
SRC_FILES=$(call find_by_name,*.yaml) $(call find_by_name,*.json)

DIST_FILES=$(foreach J,$(SRC_FILES:.yaml=.json),$(DIST)/$(J))

.PHONY: dist clean

dist: $(DIST_FILES)

ifneq ($(DIST_FILES),)

pre-install:
	@echo Pre-install check for s3triggers - OK

_install: dist
	@$(call lava_put_trigger,$(REALM),$(DIST_FILES))

uninstall: dist
	@for f in $(DIST_FILES) ; \
	do \
		trigger_id=`python3 -c 'import json, sys; print(json.load(sys.stdin)["trigger_id"])' < $$f` ; \
		aws dynamodb delete-item --table-name lava.$(REALM).s3triggers \
			--key "{ \"trigger_id\": { \"S\": \"$$trigger_id\" } }" && \
				echo s3trigger $$f: deleted ; \
	done

diff:	dist
	@tmpf=$$(mktemp) ; \
	z=1 ; \
	trap '/bin/rm -f "$$tmpf"; exit $$z' 0 ; \
	for f in $(DIST_FILES) ; \
	do \
		trigger_id=`python3 -c 'import json, sys; print(json.load(sys.stdin)["trigger_id"])' < $$f` ; \
		echo "[34m$$f ... $$trigger_id @ $(REALM)[0m" ; \
		dyn-get-item -t "lava.$(REALM).s3triggers" "trigger_id=$$trigger_id" > "$$tmpf" ; \
		[ ! -s "$$tmpf" ] && continue ; \
		json-diff --ignore '[xX]-*' "$$f" "$$tmpf" || echo ; \
	done ; \
	z=0

endif

pre-install _install uninstall:

endif

clean:
	$(RM) $(DIST_FILES)
