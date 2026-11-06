
FROM ubuntu:26.04

RUN \
    apt-get update ; \
    apt-get install --no-install-recommends -y mysql-client ; \
    mysql --version

ENTRYPOINT [ "mysql" ]
