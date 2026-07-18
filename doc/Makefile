# Makefile to build doco.

SHELL:=/bin/bash

repo_base=..

include $(repo_base)/etc/make/common.mk
include $(repo_base)/etc/make/help.mk

# ------------------------------------------------------------------------------
# Auto-help setup
#
#+ ⚠️ While you *can* run make from this directory, it's generally better to run it
#+ from the parent directory.

#- For more information, consult the lava user guide $(_URL)

HELP_CATEGORY=Miscellaneous targets

#:cat Documentation targets

# ------------------------------------------------------------------------------

export PYTHONPATH=$(repo_base)
export PATH:=$(repo_base)/etc:$(PATH)

USER_GUIDE=lava-user-guide

FORMATS=md site

MARKDOWN_SRC=$(shell find user-guide -name '*.md')
IMAGES=$(sort $(wildcard img/*.png) $(wildcard img/*.jpg) $(wildcard img/*.svg))
GIT_BRANCH:=$(shell git branch --show-current)


DOCS=$(patsubst %,$(dist)/doc/$(USER_GUIDE).%,$(FORMATS))
CUSTOM_DICT=$(CURDIR)/.aspell-dict

CFN_DIR=60-cfn

LAVA_VERSION=$(shell python3 "$(repo_base)/lava/version.py" --all)

# This gets picked up in the custom mkdocs footer template
export md_footer_rhs:=v$(LAVA_VERSION)

.PHONY:	schemas samples

all:	doc

## Build the user guide into consolidated markdown.
doc:	user-guide

user-guide: DOC_TITLE=Lava User Guide
user-guide: $(DOCS)

# Samples for jobs, connections etc.
SAMPLES=$(shell find samples -name '*.yaml' ! -name '_*' | sort)

# user-guide/18-Samples/samples.md: $(shell find samples)
#	(cd samples; ./make-samples-md.sh) > $@

user-guide/18-Samples/samples.md: samples
	samples/make-samples-md.sh "$(dist)/doc/samples" > $@

# Build a job framework sample and validate against schema. The schemas must
# have been built first.

$(dist)/doc/samples/%.yaml: samples/%.yaml
	@mkdir -p "$$(dirname "$@")"
	@category="$$(dirname "$*")" ; \
	item="$$(basename "$*")" ; \
	samples/lava-sample.py -p "$${category}_id=demo" -P '???' "$<" > "$@" ; \
	$(repo_base)/bin/lava-schema --schema-base $(dist)/schemas --type "$$category" "$@"
	@echo "Built $@"


# This target is mostly for validating the samples so we need the schemas as well
## Build DynamoDB table entry samples (jobs, connections etc.)
samples: _venv_is_on schemas $(patsubst samples/%.yaml,$(dist)/doc/samples/%.yaml,$(SAMPLES))


# Markdown as a single file.
$(dist)/doc/$(USER_GUIDE).md: user-guide/18-Samples/samples.md $(MARKDOWN_SRC) $(IMAGES) $(wildcard $(repo_base)/cfn/*.cfn.json)
	@echo "Generating $@"
	@mkdir -p $(dist)/doc
	@( \
		set -e ; \
		tmp=$$(mktemp -d) ; \
		z=1 ; \
		trap '/bin/rm -rf $$tmp; exit $z' 0 ; \
		cp -RL user-guide/. $$tmp ; \
		echo ".... Generating CFN doco" ; \
		export CFDOCPATH=cfdoc ; \
		for f in $(repo_base)/cfn/*.cfn.json; \
		do \
			cfn="$$(basename $$f)" ; \
			cfdoc --format md-mkdocs --name "$$cfn" "$$f" > "$$tmp/$(CFN_DIR)/$${cfn}.md" ; \
		done ; \
		echo ".... Merging markdown" ; \
		find $$tmp -name '*.md' -print0 | sort -z | xargs -0 -n1 sed -e '1s/^/\n/' > $@ ; \
		z=0 ; \
	)
	@cp -RL img $(dist)/doc

# Generate prepared source area for published docs. Note that we publish the
# JSON schemas as part of the doco site.
%.site: %.md schemas $(shell find mkdocs)
	@echo Generating $@
	@( \
		$(RM) -r "$@" ; \
		cp -RL mkdocs "$@" ; \
		jinja -p version="$(LAVA_VERSION)" mkdocs/docs/index.md > "$@/docs/index.md" ; \
		md-split --config "$@/mkdocs.yml" --dir "$@/docs" $< ; \
		mkdir -p "$@/docs/schemas/latest" ; \
		cp -R $(dist)/schemas/*.{json,yaml} "$@/docs/schemas/latest" ; \
	)

schemas:
	@$(MAKE) -C $(repo_base) schemas dist=dist

## Build and preview the mkdocs version of the user guide.
preview: $(dist)/doc/$(USER_GUIDE).site
	mkdocs serve -f $</mkdocs.yml --open

_publish: $(dist)/doc/$(USER_GUIDE).site
	mkdocs gh-deploy -f $</mkdocs.yml --clean

## Publish the user guide to GitHub pages (must be on *master* branch).
ifeq ($(GIT_BRANCH),master)
publish: _venv_is_on _publish

else
publish:
	$(error User guide must be published from "master" not "$(GIT_BRANCH)")
endif

## Spell check the user guide (requires **aspell**).
spell:
	@for i in $$(find user-guide -name '*.md') ; \
	do \
		echo $$i ; \
		aspell -p $(CUSTOM_DICT) check $$i ; \
	done

# ------------------------------------------------------------------------------
#:cat Miscellaneous targets

## Remove generated documents.
clean:
	$(RM) -r $(dist)/doc
