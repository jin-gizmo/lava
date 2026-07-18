# Dockerfile to set up a very basic SMB service for lava testing.

# WARNING : This is NOT a generic builder for an SMB image. It is not meant  to
#           be secure or generically useful. It is for lava testing only.

FROM ubuntu:26.04

ENV SMB_ROOT=/smb-data

RUN \
    apt-get update ; \
    apt-get install -y samba smbclient ; \
    mkdir "$SMB_ROOT"


# COPY smb.conf /etc/samba/smb.conf

# EXPOSE 139/tcp 445/tcp

# CMD smbd --foreground --no-process-group
