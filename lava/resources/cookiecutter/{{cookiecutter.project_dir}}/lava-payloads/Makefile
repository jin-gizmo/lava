# Build job payloads.

# With the default configuration, all Python scripts (*.py), Shell scripts (*.sh)
# and SQL scripts (*.sql) are generated into the dist area. For Python and Snell
# scripts, this is a plain copy operation. SQL scripts are Jinja rendered on the
# way.
#
# Jupyter notebook files (*.ipynb) will be convered to native Python.
#
# There is a a default rule for directories with names ending in .pkg which will
# zip up the contents, including any Python modules referenced in a
# requirements.txt file. The zip file should be suitable for a lava "pkg"
# payload.  No Jinja rendering is done on the contents.
#
# There is a default rule for directories with names ending in *.docker which
# will create a docker container, including any Python modules referenced in a
# requirements.txt file.

include ../etc/Makefile

ifndef REALM
%:
	$(error Run make from the parent directory - not here)
else


# ------------------------------------------------------------------------------

S3_PAYLOADS=$(call get_realm_info,lava.realm.s3_payloads)
PAYLOAD_PREFIX=$(call get_config,prefix.payload)
DOCKER_PREFIX=$(call get_config,prefix.docker_repo)

# List of files to generate

SRC_SQL=$(wildcard *.sql)
SRC_PY=$(wildcard *.py)
SRC_SH=$(wildcard *.sh)
SRC_IPYNB=$(wildcard *.ipynb)
SRC_PKG=$(wildcard *.pkg)
SRC_DOCKER=$(wildcard *.docker)
SRC_RSC=$(wildcard *.rsc)
SRC_RAW=$(wildcard *.raw)

# Files containing docker image IDs
DOCKER_IMG_FILES=$(foreach F,$(SRC_DOCKER),$(DIST)/$(basename $(F)).dockerimg)
# Rendered dockerfiles
DOCKERFILES=$(foreach F,$(SRC_DOCKER),$(DIST)/$(basename $(F)).dockerfile)
# Image names
DOCKER_IMG_NAMES=$(foreach F,$(SRC_DOCKER),$(DOCKER_PREFIX)/$(basename $(F)))

# There must be some kind of rule available to make everything in the
# DIST_FILES list. Default rules exist for:
# - SQL files that involve rendering
# - Standalone Python files that just need to be copied.
# - Standalone shell scripts that just need to be copied.
#
# For more complex bundles, add a custom rule to build the package
# into the $(DIST) directory.

DIST_FILES=\
	$(foreach F,$(SRC_SQL),$(DIST)/$(F)) \
	$(foreach F,$(SRC_PY),$(DIST)/$(F)) \
	$(foreach F,$(SRC_SH),$(DIST)/$(F)) \
	$(foreach F,$(SRC_IPYNB),$(DIST)/$(basename $(F)).py) \
	$(foreach F,$(SRC_PKG),$(DIST)/$(basename $(F)).zip) \
	$(foreach F,$(SRC_RSC),$(DIST)/$(basename $(F)).rsc) \
	$(foreach F,$(SRC_RAW),$(DIST)/$(basename $(F)).raw) \
	$(DOCKER_IMG_FILES)

.PHONY: dist clean

dist: $(DIST) $(DIST_FILES)

ifneq ($(DIST_FILES),)

# Do a test write to the payloads area
pre-install:
	@( \
		echo "$(PAYLOAD_PREFIX)" | \
			aws s3 --quiet cp - "$(S3_PAYLOADS)/__fwk__/check" ; \
		if [ $$? -ne 0 ] ; \
		then \
			echo "Cannot write to payloads area: $(S3_PAYLOADS)" ; \
			exit 1 ; \
		else \
			: ; \
		fi ; \
	)
	@echo Pre-install check for payloads - OK

_install: dist backup
	@echo "Installing payloads to $(S3_PAYLOADS)/"
	aws s3 sync "$(DIST)" "$(S3_PAYLOADS)/$(PAYLOAD_PREFIX)/" --exclude '*.docker*'
	ecr-login
	ecr-push $(DOCKER_IMG_NAMES)

uninstall: backup
	@echo "Purging $(S3_PAYLOADS)/"
	aws s3 rm "$(S3_PAYLOADS)/$(PAYLOAD_PREFIX)/" --recursive
	@for repo in $(DOCKER_IMG_NAMES) ; \
	do \
		echo "Deleting ECR repo $$repo" ; \
		aws ecr delete-repository --force --repository-name "$$repo" ; \
	done

diff:
	@echo "Diff is not supported for lava-payloads"

backup:	
	@echo "Creating backup to $(S3_PAYLOADS)/__bak__/"
	aws s3 sync "$(S3_PAYLOADS)/$(PAYLOAD_PREFIX)/" "$(S3_PAYLOADS)/__bak__/$(PAYLOAD_PREFIX)/"

endif

pre-install _install uninstall:

endif

clean:
	$(RM) $(DIST_FILES) $(DOCKERFILES)
	docker-purge $(DOCKER_IMG_NAMES)
