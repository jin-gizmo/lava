#!/bin/bash
# shellcheck disable=SC2154
# ex: sw=4 ts=4 et ai

# ------------------------------------------------------------------------------
# Install Python from source. The AWS repos are too old.
# ------------------------------------------------------------------------------

. lib/funcs.sh

require PYTHON_VERSION

export PATH=/usr/local/bin:$PATH

PREFIX="/opt/python/${PYTHON_VERSION}"
mkdir -p "$PREFIX"

mkdir /tmp/python
(
    set -e
    cd /tmp/python
    wget "https://www.python.org/ftp/python/${PYTHON_VERSION}/Python-${PYTHON_VERSION}.tgz"
    tar xf "Python-${PYTHON_VERSION}.tgz"
    cd "Python-${PYTHON_VERSION}"
    ./configure --enable-optimizations --prefix "${PREFIX}" --with-readline=editline --with-platlibdir=lib64
    # The parallel make seems to cause a disastrous race condition on
    # ARM architectures. Don't use it. :-(
    # make -j "$(nproc)" altinstall
    make altinstall
    cd /tmp
    /bin/rm -rf python

) || exit 1

set -e

PYTHON_VMAJOR=${PYTHON_VERSION%.*}

# We're going to link our version of python3 into /usr/local/bin. 
# Can't muck with /usr/bin/python3 because a security patch can reinstate that
# to an old version.

for exe in python pydoc pip
do
    /usr/sbin/update-alternatives --install /usr/local/bin/${exe}3 ${exe}3 "${PREFIX}/bin/${exe}${PYTHON_VMAJOR}" 1
done

# This should pick up the Python we just installed.
pyver=$(python3 -c "from sys import version_info as v; print(f'{v.major}.{v.minor}.{v.micro}')")
if [ "$pyver" != "$PYTHON_VERSION" ]
then
    abort "Python3 install conniption: Expected to find $PYTHON_VERSION but got $pyver"
else
    :
fi

# Now for the modules.

python3 -m pip install pip --upgrade
python3 -m pip install -r resources/requirements.txt --upgrade

for exe in "${PREFIX}/bin/"*
do
    [ -f "$exe" -a -x "$exe" ] || continue
    [ -f "/usr/local/bin/$(basename "$exe")" ] && continue
    ln -s "$exe" /usr/local/bin
done
