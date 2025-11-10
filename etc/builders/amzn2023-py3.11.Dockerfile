# Dockerfile to build an image suitable for building the lava pkg.

FROM amazonlinux:2023

ARG python_version=3.11.14

# This is arg, not env, because we want to use it now but don't want to bake it
# in to the image.
ARG PIP_INDEX_URL

RUN \
	set -e ; \
	export PIP_INDEX_URL="${PIP_INDEX_URL}" ; \
	dnf update -y ; \
	dnf -y groupinstall "Development Tools" ; \
	dnf -y install wget openssl-devel bzip2-devel libffi-devel sqlite-devel ; \
	dnf -y install libedit-devel readline-devel postgresql-devel unixODBC-devel ; \
	mkdir /tmp/python ; \
	cd /tmp/python/ ; \
	wget "https://www.python.org/ftp/python/${python_version}/Python-${python_version}.tgz" ; \
	tar xf "Python-${python_version}.tgz" ; \
	cd "Python-${python_version}" ; \
	./configure --enable-optimizations --with-readline=editline --with-platlibdir=lib64 ; \
	make install ; \
	cd /tmp ; \
	/bin/rm -rf python ; \
	python3 --version ; \
	python3 -m pip install pip setuptools awscli packaging -U ; \
