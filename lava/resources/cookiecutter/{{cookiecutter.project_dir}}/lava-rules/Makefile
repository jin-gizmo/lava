# # Create Lava EventBridge rules. The specifications can be in YAML
# (preferred) or JSON.
#
# With the default configuration below all *.yaml and *.json files will be
# Jinja rendered one for one into the dist area with YAML files converted to
# JSON on the way. This is probably ok for most situations.
#
# NOTE:	The Jinja rendering uses non-standard Jinja delimiters to avoid
# 	conflict with normal Jinja syntax used by Lava. See README.md.

include ../etc/Makefile

EVENTBUS=default

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
	@echo Pre-install check for EventBridge rules - OK

_install: dist
	event-put-rule $(DIST_FILES)

uninstall: dist
	@for f in $(DIST_FILES) ; \
	do \
		rule_id=$$(python3 -c 'import json, sys; print(json.load(sys.stdin)["rule_id"])' < $$f) ; \
		if [ "$$rule_id" == "" ] ; \
		then \
			echo "$$f: Cannot get rule_id" ; \
			exit 1 ; \
		else : ; \
		fi ; \
		set -- $$( \
			aws events list-targets-by-rule --rule "$$rule_id" \
				--query 'Targets[].Id' --output text --no-paginate \
			) ; \
		if [ $$1 != "" ] ; \
		then \
			aws events remove-targets --event-bus-name "$(EVENTBUS)" \
				--rule "$$rule_id" --ids $$* && echo "Rule $$rule_id: $$# targets deleted" ; \
		else \
			: ; \
		fi ; \
		aws events delete-rule --event-bus-name "$(EVENTBUS)" --name "$$rule_id" && \
			echo "Rule $$rule_id: deleted" ; \
	done

diff:
	@echo Diff is not supported for lava-rules

endif

pre-install _install uninstall:

endif

clean:
	$(RM) $(DIST_FILES)
