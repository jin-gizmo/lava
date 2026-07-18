# Simple Makefile to generate CloudFormation doco.

repo_base=..

include $(repo_base)/etc/make/common.mk
include $(repo_base)/etc/make/help.mk

# ------------------------------------------------------------------------------
# Auto-help setup
#
#+ This makefile is used to build the lava CloudFormation templates and the
#+ associated documentation for inclusion in the user guide.
#+ 
#+ ⚠️  While you *can* run make from this directory, it's generally better to run it
#+ from the parent directory.

#- For more information, consult the lava user guide $(_URL)

HELP_CATEGORY=Targets

# ------------------------------------------------------------------------------
MD_FILES=$(patsubst %.cfn.json,$(dist)/cfn/%.cfn.md,$(wildcard *.cfn.json))
HTML_FILES=$(patsubst %.cfn.json,$(dist)/cfn/%.cfn.html,$(wildcard *.cfn.json))

DIST_CFN_FILES=$(patsubst %.cfn.json,$(dist)/cfn/%.cfn.json,$(wildcard *.cfn.json))

LAVA_VERSION_NUM=$(shell python3 ../lava/version.py)

.PHONY: dist

# Inject version info into the CFN
$(dist)/cfn/%.cfn.json: %.cfn.json
	../etc/json-inject --no-sort \
		--deep-param Outputs.Version.Value="$(LAVA_VERSION_NUM)" \
		< $< > $@

# Generate markdown doco from the generated CFN not the base source
# $(dist)/doc/cfn/%.cfn.md: $(dist)/cfn/%.cfn.json
%.cfn.md: %.cfn.json
	cfdoc -f md $< > $@

# Generate HTML
%.cfn.html: %.cfn.json
	cfdoc -f html $< > $@

.PHONY:	error all md html clean

all:	cfn doc

dist:	$(dist)/cfn

$(dist)/cfn:
	mkdir -p $@
	

## Build the CloudFormation templates.
cfn:	_venv_is_on dist $(DIST_CFN_FILES)

## Build the CloudFormation documentation.
doc:	_venv_is_on dist md html

md:	_venv_is_on dist $(MD_FILES)

html:	_venv_is_on dist $(HTML_FILES)

## Remove the generated templates and documents.
clean:	
	$(RM) -r $(dist)/cfn
