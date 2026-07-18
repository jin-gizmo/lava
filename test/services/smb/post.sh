#!/bin/bash

# Post shutdown cleanup

CONTAINER=lava-test-smb

echo "🔵 $CONTAINER: starting cleanup"

/bin/rm -rf services/smb/share.x

echo "✅ $CONTAINER: cleanup done"
