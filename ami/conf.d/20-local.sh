#!/bin/bash
# ex: sw=4 ts=4 et ai

# ------------------------------------------------------------------------------
# Install the local utilities
# ------------------------------------------------------------------------------

set -e
shopt -s nullglob

for f in resources/local/lib/*; do install -m644 -oroot -groot "$f" /usr/local/lib; done
for f in resources/local/man/*; do install -m644 -oroot -groot "$f" /usr/local/share/man/man1; done
for f in resources/local/bin/*; do install -m755 -oroot -groot "$f" /usr/local/bin; done
for f in resources/local/sbin/*; do install -m755 -oroot -groot "$f" /usr/local/sbin; done
for f in resources/local/etc/*; do install -m755 -oroot -groot "$f" /usr/local/etc; done
