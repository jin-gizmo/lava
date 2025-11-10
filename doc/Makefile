# Makefile to build doco.

dist=../dist

export PYTHONPATH=..

USER_GUIDE=lava-user-guide

FORMATS=md site

MARKDOWN_SRC=$(shell find user-guide -name '*.md')
IMAGES=$(sort $(wildcard img/*.png) $(wildcard img/*.jpg) $(wildcard img/*.svg))
GIT_BRANCH:=$(shell git branch --show-current)

DOCS=$(patsubst %,$(dist)/doc/$(USER_GUIDE).%,$(FORMATS))
CUSTOM_DICT=$(CURDIR)/.aspell-dict

CFN_DIR=60-cfn

LAVA_VERSION=$(shell python3 ../lava/version.py --all)

# This gets picked up in the custom mkdocs footer template
export md_footer_rhs:=v$(LAVA_VERSION)

all:	doc

doc:	user-guide

user-guide: DOC_TITLE=Lava User Guide
user-guide: $(DOCS)


clean:
	$(RM) -r $(dist)/doc

user-guide/18-Samples/samples.md: $(shell find ../dev-tools/templates)
	(cd ../dev-tools; ./make-template-md.sh) > $@

# Markdown as a single file.
$(dist)/doc/$(USER_GUIDE).md: user-guide/18-Samples/samples.md $(MARKDOWN_SRC) $(IMAGES) $(wildcard ../cfn/*.cfn.json)
	@echo "Generating $@"
	@mkdir -p $(dist)/doc
	@( \
		set -e ; \
		tmp=$$(mktemp -d) ; \
		z=1 ; \
		trap '/bin/rm -rf $$tmp; exit $z' 0 ; \
		cp -R user-guide/. $$tmp ; \
		echo ".... Generating CFN doco" ; \
		export CFDOCPATH=cfdoc ; \
		for f in ../cfn/*.cfn.json; \
		do \
			cfn="$$(basename $$f)" ; \
			cfdoc --format md-mkdocs --name "$$cfn" "$$f" > "$$tmp/$(CFN_DIR)/$${cfn}.md" ; \
		done ; \
		echo ".... Merging markdown" ; \
		find $$tmp -name '*.md' -print0 | sort -z | xargs -0 -n1 sed -e '1s/^/\n/' > $@ ; \
		z=0 ; \
	)
	@cp -r img $(dist)/doc

# Generate prepared source area for published docs
%.site: %.md $(shell find mkdocs)
	@echo Generating $@
	@( \
		$(RM) -r "$@" ; \
		cp -RL mkdocs "$@" ; \
		../etc/jinja -p version="$(LAVA_VERSION)" mkdocs/docs/index.md > "$@/docs/index.md" ; \
		../etc/md-split --config "$@/mkdocs.yml" --dir "$@/docs" $< ; \
	)

# Serve the user guide on port 8000 for local review
preview: $(dist)/doc/$(USER_GUIDE).site
	mkdocs serve -f $</mkdocs.yml --open

_publish: $(dist)/doc/$(USER_GUIDE).site
	mkdocs gh-deploy -f $</mkdocs.yml --clean

ifeq ($(GIT_BRANCH),master)
publish: _publish

else
publish:
	$(error User guide must be published from "master" not "$(GIT_BRANCH)")
endif

# Spell check the user guide
spell:
	@for i in $$(find user-guide -name '*.md') ; \
	do \
		echo $$i ; \
		aspell -p $(CUSTOM_DICT) check $$i ; \
	done
