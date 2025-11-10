# Makefile to build developer tools

repo_base=..
dist=$(repo_base)/dist

LAVA_VERSION=$(shell $(repo_base)/lava/version.py)

TEMPLATE_DIR=$(repo_base)/lava/resources

.PHONY: clean tools job-framework

help:
	@echo Don\'t run make from here please -- run it from parent directory

clean:
	$(RM) -r $(dist)/dev-tools

all:	tools

tools:	_deprecation job-framework

_deprecation:
	@echo
	@echo "[31m+------------------------------------------------------------------------------+[0m"
	@echo "[31m|   dev-tools/Makefile is deprecated. Tell us if you think you still need it.  |[0m"
	@echo "[31m+------------------------------------------------------------------------------+[0m"
	@echo

job-framework: $(dist)/dev-tools/lava-job-framework-$(LAVA_VERSION).zip

$(dist)/dev-tools/lava-job-framework-$(LAVA_VERSION).zip: $(shell find $(TEMPLATE_DIR))
	@echo Generating $@
	@mkdir -p $(dist)/dev-tools
	@( \
		set -e ; \
		z=1 ; \
		tmp=$$(mktemp -d) ; \
		trap '/bin/rm -rf $$tmp; exit $$z' 0 ; \
		zip -q -r - $(TEMPLATE_DIR) \
			--exclude \
				'*dist/*' \
				'*.pyc' \
				'*__pycache__/*' \
				'*.swp' \
				'*.zip' \
				'*.tar.*' \
				'*-info/*' \
				'*/.DS_Store' \
			> $$tmp/x.zip ; \
		mkdir $$tmp/etc ; \
		../lava/version.py -a > "$$tmp/etc/version" ; \
		(set -e ; cd $$tmp ; zip -q -u x.zip etc/version) ; \
		cp $$tmp/x.zip $@ ; \
		z=0 ; \
	) || (echo Failed -- Removing $@ ; $(RM) $@)
