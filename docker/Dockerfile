# syntax=docker/dockerfile:1
# ------------------------------------------------------------------------------
# Build a lava container.
#
# ex: sw=4 ts=4 ai et
#
# Context must be the directory containing the following directories:
#
#   pkg:        This directory contains lava install package plus any other
#               required software packages that can't be obtained directly at
#               build time (e.g. the Oracle client).
#   os/type:    A directory containing os type specific build scripts. The
#               type will be something like "centos", "alpine" etc.
#
# Build-args:
#
#   base:       The base image. e.g centos:latest
#   os:         Name of the underlying Linux OS image type. e.g. centos
#   type:       full or base. If full, the base image must be a compatible lava
#               base image.
#   version:    The lava version. e.g. 7.1.0
#
# Author: Murray Andrews
# ------------------------------------------------------------------------------

# ------------------------------------------------------------------------------
# WARNING:  Docker is incredibly fragile in its handling of ARGs. Be VERY
#           careful with use of double quotes.
# ------------------------------------------------------------------------------


ARG base=this-must-be-specified-as-a-build-arg
FROM ${base}

# ------------------------------------------------------------------------------
# Build args

ARG os
ARG type=base
ARG version
ARG lava_base=/opt/lava

# ------------------------------------------------------------------------------

ENV \
    LAVA_BASE="${lava_base}" \
    LAVA_VERSION="${version}" \
    PYTHONPATH="${lava_base}:${lava_base}/pylib" \
    LANG=C.UTF-8 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

RUN --mount=type=bind,source=.,target=/tmp/lava \
    cd /tmp/lava ; \
    for f in ${type}-* ; \
    do \
        [ ! -x $f ] && continue ; \
        echo "[35m** Run ${f}[0m" >&2 ; \
        ./$f; \
        [ $? -ne 0 ] && echo "[1;31mABORT: $f (Status $?)[0m" && exit 1; \
    done ; \
    echo Done

CMD ["/bin/bash"]
