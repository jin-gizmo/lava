FROM node:24-alpine

ARG NPM_CONFIG_REGISTRY
ENV NPM_CONFIG_REGISTRY=$NPM_CONFIG_REGISTRY

# The --host option was introduced as a breaking (!!) change in 0.12.1.
RUN \
    npm install -g "emulate@>=0.12.1" \
    && addgroup -S emulate \
    && adduser -S -G emulate -h /emulate emulate

USER emulate

WORKDIR /emulate

# Expose a range of ports in case we want to emulate multiple services
EXPOSE 4000 4001 4002 4003 4004 4005 4006 4007 4008 4009 4010 4011

# v0.12.1 change the host from 0.0.0.0 to 127.0.0.1 which is useless in a
# container so we need to specify host explicitly.
ENTRYPOINT ["emulate", "start", "--host", "0.0.0.0"]
