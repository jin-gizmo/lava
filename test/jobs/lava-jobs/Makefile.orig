# Create Lava job specifications. The jobs can be in YAML (preferred) or JSON.

# With the default configuration below all *.yaml and *.json files will be
# Jinja rendered one for one into the dist area with YAML files converted to
# JSON on the way.
#
# NOTE:	The Jinja rendering uses non-standard Jinja delimiters to avoid
# 	conflict with normal Jinja syntax used by Lava. See README.md.
#
# You will need to customise this file if you don't have a 1-1 mapping between
# source in this directory and outputs in dist. e.g. If one template file is
# used to generate multiple jobs. In that case you will need custom build rules.
#
# For example this shows how a single template file "template.yaml" could be
# used to generate template-a.json, template-b.json, template-c.json in dist
# area
#
# # Here is our list.
# ABC=a b c
# # Generate the names of "pseudo" source files. We don't actually create them.
# # Just tricking DIST_FILES into forcing final jobs to be built.
# SRC_FILES=$(foreach F,$(ABC),template-$(F).yaml)
# # Now we need a custom rule for the final jobs. Add custom rendering params
# # to the Jinja process as required. The "item" rendering var will be set
# # to a or b or c as appropriate.
# $(DIST)/template-%.json:
#	 jinja --delimiter \< --file $(CONFIG) -p item=$* template.yaml | yaml2json > $@

# include must go first!
include ../etc/Makefile

ifndef REALM

%:
	$(error Run make from the parent directory - not here)

else

# List of files to generate
SRC_FILES=$(call find_by_name,*.yaml) $(call find_by_name,*.json)

DIST_FILES=$(foreach J,$(SRC_FILES:.yaml=.json),$(DIST)/$(J))
LEFT_PAREN=(
SRC_DAGS=$(shell grep -l 'lava\.dag$(LEFT_PAREN)' $(SRC_FILES) /dev/null)
DIST_DAGS=$(foreach J,$(SRC_DAGS:.yaml=.json),$(DIST)/$(J))

.PHONY: dist clean

# Jobs using lava.dag() must be rebuilt as we don't know if dag info has changed.
_clean_dags:
	@( \
		if [ "$(DIST_DAGS)" != "" ] ; \
		then $(RM) $(DIST_DAGS); \
		else : ; \
		fi \
	)

dist: _clean_dags $(DIST_FILES)

pre-install:
	@echo Pre-install check for jobs - OK

_install: dist
	@$(call lava_put_job,$(REALM),$(DIST_FILES))

uninstall: dist
	@for f in $(DIST_FILES) ; \
	do \
		job_id=`python3 -c 'import json, sys; print(json.load(sys.stdin)["job_id"])' < $$f` ; \
		aws dynamodb delete-item --table-name lava.$(REALM).jobs \
			--key "{ \"job_id\": { \"S\": \"$$job_id\" } }" && \
				echo Job $$job_id: deleted ; \
	done

diff:	dist
	@tmpf=$$(mktemp) ; \
	z=1 ; \
	trap '/bin/rm -f "$$tmpf"; exit $$z' 0 ; \
	for f in $(DIST_FILES) ; \
	do \
		job_id=`python3 -c 'import json, sys; print(json.load(sys.stdin)["job_id"])' < $$f` ; \
		echo "[34m$$f ... $$job_id @ $(REALM)[0m" ; \
		dyn-get-item -t "lava.$(REALM).jobs" "job_id=$$job_id" > "$$tmpf" ; \
		[ ! -s "$$tmpf" ] && continue ; \
		json-diff --ignore '[xX]-*' "$$f" "$$tmpf" || echo ; \
	done ; \
	z=0

endif

clean:
	$(RM) $(DIST_FILES)
