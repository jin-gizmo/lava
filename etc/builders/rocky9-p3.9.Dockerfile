# Dockerfile to build an image suitable for building the lava pkg.

FROM rockylinux:9

# This is arg, not env, because we want to use it now but don't want to bake it
# in to the image.
ARG PIP_INDEX_URL

RUN \
	set -e ; \
	export PIP_INDEX_URL="${PIP_INDEX_URL}" ; \
	dnf update -y ; \
	dnf install 'dnf-command(config-manager)' -y $QUIET ; \
	dnf config-manager --set-enabled crb ; \
	dnf install python3 python3-devel -y ; \
	dnf install util-linux gcc gcc-c++ make tar bzip2 cpio findutils -y ; \
	dnf install unixODBC-devel -y ; \
	dnf install postgresql-devel -y ; \
	python3 -m pip install pip setuptools packaging -U
