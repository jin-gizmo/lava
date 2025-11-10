# Automate generation of lambda code bundles

SHELL:=/bin/bash
APP=lava

repo_base=..

include $(repo_base)/etc/Makefile

# ------------------------------------------------------------------------------
#  Generic from here on

LAMBDAS=dispatch s3trigger stop metrics
LAVA_VERSION=$(shell python3 ../lava/version.py)

pkg_dir=$(dist)/lambda
PKGS=$(foreach lambda,$(LAMBDAS),$(pkg_dir)/$(lambda)-$(LAVA_VERSION).zip)
PIP_FILES=$(wildcard */*.in)
REQ_FILES=$(foreach P,$(PIP_FILES:.in=.txt),$(P))
PIP_INDEX_URL=$(shell ../etc/pip-index-url)

# We build the lambdas on Amazon Linux 2023 Python 3.13. Doesn't matter greatly
# as the result will run fine on Python 3.11+.
runtime=amzn2023-py3.13
platform=linux/arm64

.PHONY: help clean pkg builder
.PRECIOUS: $(REQ_FILES)


# ------------------------------------------------------------------------------
help:
	@echo
	@echo What do you want to make?  Available targets are:
	@echo
	@echo "[1mInstallation related targets:[0m"
	@echo "   pkg:     Make the install packages."
	@echo
	@echo "[1mMiscellaneous targets:[0m"
	@echo "   clean:   Remove the generated packages."
	@echo "   help:    Print this help text."
	@echo

# ------------------------------------------------------------------------------
#

FORCE:

# We want these to build always as the venv could have something new in it.
# However we take care to not replace the .txt file if its unchanged to minimise
# unnecessary rebuilds. Deliberately avoid running inside docker.
%.txt:	FORCE
	@( \
		[ -f /.dockerenv ] && exit 0 ; \
		z=0; TMP=$$(mktemp) ; trap '/bin/rm -f $$TMP; exit $$z' 0 ; \
		../etc/pip-freeze < $*.in > $$TMP || exit ; \
		if cmp -s $@ $$TMP ; \
		then \
			: echo $@ is up to date: ; \
		else \
			cp $$TMP $@ ; \
			echo "[32mUpdating $@[0m" ; \
		fi ; \
		z=0 ; \
	)


# TODO: The wildcard here doesn't actually work in terms of detecting dependencies
$(pkg_dir)/%-$(LAVA_VERSION).zip: %/requirements.txt $(wildcard %/*.py) $(wildcard ../lava/*.py) $(wildcard ../lib/*.py)
	mkdir -p $(pkg_dir)
	./pkg.sh -d $(pkg_dir) $(shell basename $@ | sed s/-.*//) || $(RM) $@

all:	pkg

lambda:	pkg

_pkg:	$(PKGS)

pkg:	$(REQ_FILES)
	@( \
		echo "[32mContainer based build for $(runtime)[0m" ; \
		builder="localhost:$(REGISTRY_LOCAL_PORT)/build/lava/$(runtime)" ; \
		if ! docker images --format "{{.Repository}}" | grep -q "$$builder" ; \
		then \
			echo "No builder available for runtime=$(runtime). Try:" ; \
			echo "    docker pull $$builder" ; \
			echo "or ..." ; \
			echo "    make builder runtime=$(runtime)" ; \
			exit 1 ; \
		fi ; \
		docker run  --rm -t --user $(shell id -u):$(shell id -g) -w /lava/build \
			--platform="$(platform)" \
			-v $(realpath .):/lava/build \
			-v $(realpath $(dist)):/lava/dist \
			-v $(realpath ../lava):/lava/lava \
			-v $(realpath ../etc):/lava/etc \
			-v ~/.aws:/lava/.aws \
			-e PIP_INDEX_URL="$(PIP_INDEX_URL)" \
			"$$builder" \
			make _pkg ; \
	)

clean:
	echo $(RM) $(PKGS)
