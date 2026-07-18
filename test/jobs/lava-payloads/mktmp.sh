#!/bin/bash

echo Test shell script for lava to create temp dir and file.

echo TMPDIR is $TMPDIR

echo Temp file is $(mktemp)
echo Temp dir is $(mktemp -d)

ls -laR
