# Dockerfile to build an image suitable for building the lava pkg.

FROM amazonlinux:2023

# This is arg, not env, because we want to use it now but don't want to bake it
# in to the image.
ARG PIP_INDEX_URL

RUN \
	set -e ; \
	export PIP_INDEX_URL="${PIP_INDEX_URL}" ; \
	dnf -y update ; \
	dnf -y groupinstall "Development Tools" ; \
	dnf -y install wget python3-devel openssl-devel bzip2-devel libffi-devel sqlite-devel ; \
	dnf -y install postgresql-devel ; \
	dnf -y install unixODBC-devel ; \
	dnf -y install python3-pip ; \
	python3 -m pip install packaging ; \
	python3 --version
