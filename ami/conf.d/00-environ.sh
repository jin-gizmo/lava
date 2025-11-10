#!/bin/bash
# ex: sw=4 ts=4 et ai

. lib/funcs.sh

# ------------------------------------------------------------------------------
require S3BUCKET S3PREFIX
require PYTHON_VERSION
require TIMEZONE
require REPO_UPGRADE
require OS
require AWS_DEFAULT_REGION

# Backoff sleeps while waiting for the IAM role to provide creds
AWS_CREDS_BACKOFF=(0 10 10 10 20 20 20 30 30 30 60 60 60 60 60 120)

# ------------------------------------------------------------------------------
echo "++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++"
echo "+                               BUILD ENVIRONMENT                              +"
echo "++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++"
env | sort
echo "++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++"

# ------------------------------------------------------------------------------
# It can sometimes take a long time for AWS to make access creds available to a
# a new instance, so we need to check and backoff and retry. I know!
info "Checking AWS credentials are available"
for t in "${AWS_CREDS_BACKOFF[@]}"
do
    [ "$t" -ne 0 ] && warning "    ... sleeping for $t seconds"
    sleep "$t"
    whoami=$(aws sts get-caller-identity --query Arn --output text) && break
done

[ "$whoami" == "" ] && error "Could not get AWS credentials and out of retries"
info "I am $whoami"

# ------------------------------------------------------------------------------
echo "++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++"
echo "                                  S3 CONTENTS                                  +"
echo "++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++"
# shellcheck disable=SC2154
aws s3 ls "$S3BUCKET/$S3PREFIX" --rec || exit 1
echo "++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++"
