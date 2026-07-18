
FROM ubuntu:26.04

RUN \
    apt-get update ; \
    apt-get install -y mariadb-client ; \
    mysql --version

ENTRYPOINT [ "mysql" ]
