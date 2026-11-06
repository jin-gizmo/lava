FROM ministackorg/ministack

RUN --mount=type=bind,from=etc,target=/tmp/lava/etc \
    apk add --no-cache jq envsubst wget openssh-keygen ; \
    wget -q -O /tmp/get-pip.py https://bootstrap.pypa.io/get-pip.py \
        && python3 /tmp/get-pip.py --root-user-action ignore \
        && /bin/rm -f /tmp/get-pip.py ; \
    python3 -m pip install --root-user-action ignore python-dotenv ; \
    cp /tmp/lava/etc/ssmp /usr/local/bin ; \
    chmod 755 /usr/local/bin/ssmp
