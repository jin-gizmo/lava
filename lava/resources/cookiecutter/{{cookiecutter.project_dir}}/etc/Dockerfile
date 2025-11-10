# Default Dockerfile for the lava job framework.

# BASE_IMG should generally be overridden as a build arg from the config file
ARG BASE_IMG=ghcr.io/jin-gizmo/lava/amzn2023/base
FROM $BASE_IMG

SHELL ["/bin/bash", "-c"]

# ------------------------------------------------------------------------------
# Setup a lava user that will own the code. Note that the lava worker will not
# run the code as this user but will run as the worker user / group IDs.

RUN \
	source /etc/os-release ; \
	echo OS is $ID >&2 ; \
	if [ "$ID" = "alpine" ] ; \
	then \
		addgroup -g 99999 lava ; \
		adduser -D -u 99999 -G lava -h /lava lava ; \
	else \
		groupadd -g 99999 lava ; \
		useradd -u 99999 -g lava -d /lava lava ; \
	fi

COPY --chown=lava:lava . /lava/

ARG PIP_INDEX_URL

ENV \
    PIP_INDEX_URL=${PIP_INDEX_URL} \
    LANG=C.UTF-8 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# ------------------------------------------------------------------------------
# Do package updates and install the payload.

RUN \
	(yum > /dev/null 2>&1; [ $? -ne 127 ] && echo Doing yum updates && yum update -y && yum clean all && rm -rf /var/cache/yum) ; \
	(apt-get > /dev/null 2>&1; [ $? -ne 127 ] && echo Doing apt updates && apt-get update && apt-get upgrade -y && apt-get clean) ; \
	(apk > /dev/null 2>&1; [ $? -ne 127 ] && echo Doing apk updates && apk update && apk upgrade) ; \
	cd ~lava ; \
	[ -f requirements.txt ] && \
		python3 -m pip --no-cache-dir install --no-warn-script-location \
			-r requirements.txt --upgrade ; \
	[ -f requirements-nodeps.txt ] && \
		python3 -m pip --no-cache-dir install --no-warn-script-location \
			-r requirements.txt --upgrade --no-deps ; \
	find . -perm -0100 -exec chmod go+x '{}' ';' ; \
	find . -perm -0400 -exec chmod go+r '{}' ';' ; \
	chown -R lava:lava . ; \
	echo Done

USER lava
