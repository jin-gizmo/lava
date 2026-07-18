FROM node:24-alpine

ARG NPM_CONFIG_REGISTRY
ENV NPM_CONFIG_REGISTRY=$NPM_CONFIG_REGISTRY

RUN \
    npm install -g emulate \
    && addgroup -S emulate \
    && adduser -S -G emulate -h /emulate emulate

USER emulate

WORKDIR /emulate

# Expose a range of ports in case we want to emulate multiple services
EXPOSE 4000 4001 4002 4003 4004 4005 4006 4007 4008 4009 4010 4011

ENTRYPOINT ["emulate"]
