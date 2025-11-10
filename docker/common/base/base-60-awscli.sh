#!/bin/bash

# This needs to happen after lava because awscli often requires old versions of
# modules used by lava. Very annoying.

python3 -m pip --no-cache-dir install 'pip>=23.3' 'awscli>=1.18.200' --upgrade
