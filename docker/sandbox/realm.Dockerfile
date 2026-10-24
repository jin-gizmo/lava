# ------------------------------------------------------------------------------
# This Dockerfile builds a functional sandbox lava realm based on the MiniStack
# AWS emulator.
#
# Use `make sandbox` to build the image, rather than trying to do it by running
# this file directly. There are a bunch of build context directories involved
# that need to be done right. The makefile handles that.
# ------------------------------------------------------------------------------

FROM ministackorg/ministack

ARG GATEWAY_PORT=4566
ARG LAVA_VERSION
ARG LAVA_REALM=sandbox
ARG LAVA_WORKER=dev

# Ministack config
ENV \
    MINISTACK_ACCOUNT_ID="123456789012" \
    GATEWAY_PORT=${GATEWAY_PORT} \
    LAMBDA_EXECUTOR="local" \
    MINISTACK_REGION="us-east-1" \
    S3_DATA_DIR="/tmp/ministack-data/s3"

# We need AWS_DEFAULT_REGION because ministack has v1 AWS CLI.
ENV \
    LAVA_REALM="${LAVA_REALM}" \
    LAVA_WORKER="${LAVA_WORKER}" \
    LAVA_VERSION="${LAVA_VERSION}" \
    AWS_ENDPOINT_URL="http://localhost:${GATEWAY_PORT}" \
    AWS_DEFAULT_REGION="${MINISTACK_REGION}"

RUN --mount=type=bind,from=dist_cfn,target=/tmp/lava/cfn \
    --mount=type=bind,from=dist_lambda,target=/tmp/lava/lambda \
    --mount=type=bind,from=etc,target=/tmp/lava/etc \
    --mount=type=bind,from=test_services_ministack,target=/tmp/lava/ministack \
    --mount=type=bind,from=docker_sandbox,target=/tmp/lava/sandbox \
    if [ "${LAVA_VERSION}" = "" ] ; \
    then echo "❌ LAVA_VERSION must be set" && exit 1 ; \
    else true ; \
    fi ; \
    apk add jq envsubst sqlite wget ; \
    wget -q -O /tmp/get-pip.py https://bootstrap.pypa.io/get-pip.py \
        && python3 /tmp/get-pip.py --root-user-action ignore \
        && /bin/rm -f /tmp/get-pip.py ; \
    python3 -m pip install --root-user-action ignore python-dotenv ; \
    mkdir -p /lava/lambda ; \
    T=/tmp/lava ; \
    cp $T/lambda/*${LAVA_VERSION}.zip /lava/lambda ; \
    cp -R $T/cfn /lava/cfn ; \
    cp -R $T/ministack/conf /lava/conf ; \
    cp -R $T/sandbox/data /lava/data ; \
    find /lava -type d -print0 | xargs -0r chmod 755 ; \
    find /lava -type f -print0 | xargs -0r chmod 644 ; \
    find /lava -name '*.bash' -o -name '*.sh' -print0 | xargs -0r chmod 755 ; \
    cp $T/etc/ssmp /usr/local/bin ; \
    chmod 755 /usr/local/bin/ssmp ; \
    /bin/rm -rf /docker-entrypoint-initaws.d/ready.d ; \
    cp -R $T/ministack/init.d/post-init /docker-entrypoint-initaws.d/ready.d ; \
    chown -R ministack /lava /docker-entrypoint-initaws.d/ready.d ; \
    chgrp -R ministack /lava /docker-entrypoint-initaws.d/ready.d ;

# The default health check for Ministack relies on the "health" endpoint. This
# comes good before the realm initialisation happens so it's not ideal in this
# case. So we switch to the "ready" endpoint. The challenge is we need to allow
# enough start period for the initial setup to complete.
HEALTHCHECK --interval=10s --timeout=3s --retries=3 \
            --start-period=120s --start-interval=1s \
  CMD python -c "import os,ssl,urllib.request as r; \
    t=os.environ.get('USE_SSL','').strip().lower() in ('1','true','yes'); \
    r.urlopen(('https' if t else 'http')+'://localhost:4566/_ministack/ready', \
    context=ssl._create_unverified_context() if t else None)" || exit 1
