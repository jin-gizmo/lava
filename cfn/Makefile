# Simple Makefile to generate CloudFormation doco.

dist=../dist

CFDOC=cfdoc

MD_FILES=$(patsubst %.cfn.json,$(dist)/cfn/%.cfn.md,$(wildcard *.cfn.json))
HTML_FILES=$(patsubst %.cfn.json,$(dist)/cfn/%.cfn.html,$(wildcard *.cfn.json))

DIST_CFN_FILES=$(patsubst %.cfn.json,$(dist)/cfn/%.cfn.json,$(wildcard *.cfn.json))

LAVA_VERSION_NUM=$(shell python3 ../lava/version.py)

.PHONY: dist

# Inject version info into the CFN
$(dist)/cfn/%.cfn.json: %.cfn.json
	../etc/json-inject \
		-d Parameters.Version.Default="$(LAVA_VERSION_NUM)" \
		-j Parameters.Version.AllowedValues='["$(LAVA_VERSION_NUM)"]' \
		< $< > $@

# Generate markdown doco from the generated CFN not the base source
# $(dist)/doc/cfn/%.cfn.md: $(dist)/cfn/%.cfn.json
%.cfn.md: %.cfn.json
	$(CFDOC) -f md $< > $@

# Generate HTML
%.cfn.html: %.cfn.json
	$(CFDOC) -f html $< > $@

.PHONY:	error all md html clean

all:	cfn doc

dist:	$(dist)/cfn

$(dist)/cfn:
	mkdir -p $@
	

cfn:	dist $(DIST_CFN_FILES)

doc:	dist md html

md:	dist $(MD_FILES)

html:	dist $(HTML_FILES)

clean:	
	$(RM) -r $(dist)/cfn
