# Makefile to build developer tools

repo_base=..

include $(repo_base)/etc/make/common.mk
include $(repo_base)/etc/make/help.mk

# ------------------------------------------------------------------------------
# Auto-help setup
#
#+ This makefile is used to build the lava job framework bundle.
#+ 
#+ While you *can* run make from this directory, it's generally better to run it
#+ from the parent directory.

#- For more information, consult the lava user guide $(_URL)

HELP_CATEGORY=Targets

# ------------------------------------------------------------------------------
LAVA_VERSION=$(shell $(repo_base)/lava/version.py)

TEMPLATE_DIR=$(repo_base)/lava/resources

.PHONY: clean tools job-framework

## Remove the generated artefacts.
clean:
	$(RM) -r $(dist)/dev-tools

all:	tools

## Build the lava job framework.
tools:	_venv_is_on job-framework

job-framework: $(dist)/dev-tools/lava-job-framework-$(LAVA_VERSION).zip

$(dist)/dev-tools/lava-job-framework-$(LAVA_VERSION).zip: $(shell find $(TEMPLATE_DIR))
	@echo Generating $@
	@mkdir -p $(dist)/dev-tools
	@( \
		set -e ; \
		z=1 ; \
		tmp=$$(mktemp -d) ; \
		trap '/bin/rm -rf $$tmp; exit $$z' 0 ; \
		cp -RL $(TEMPLATE_DIR)/ $$tmp ; \
		../lava/version.py -a > "$$tmp/cookiecutter/{{cookiecutter.project_dir}}/etc/version" ; \
		( \
			set -e ; \
			cd $$tmp ; \
			zip -q -r - . \
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
		) ; \
		cp $$tmp/x.zip $@ ; \
		z=0 ; \
	) || (echo Failed -- Removing $@ ; $(RM) $@)
