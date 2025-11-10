#!/bin/bash

# Install AWS CLI v2

set -e

mkdir -p /opt/awscliv2

TMP=$(mktemp -d)
z=0
trap '/bin/rm -rf "$TMP"; exit $z' 0

cd "$TMP"

curl "https://awscli.amazonaws.com/awscli-exe-linux-$(arch).zip" -o awscliv2.zip
unzip -q -u awscliv2.zip

./aws/install --bin-dir /usr/bin --install-dir /opt/awscliv2
z=$?
