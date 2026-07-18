
FROM ubuntu:26.04

RUN \
    apt-get update ; \
    apt-get install -y postgresql-client ; \
    psql --version

ENTRYPOINT [ "psql" ]
