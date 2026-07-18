FROM axllent/mailpit

COPY mailpit/docker-entrypoint-init.sh /

RUN \
    apk add openssl ; \
    mkdir /mail ; \
    chown mail /mail ; \
    chgrp mail /mail ; \
    chmod 755 /docker-entrypoint-init.sh

USER mail

WORKDIR /mail

# Expose a range of ports in case we want to emulate multiple services
EXPOSE 1025 8025

ENTRYPOINT ["/docker-entrypoint-init.sh"]
