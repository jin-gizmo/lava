#!/bin/bash
# ex: sw=4 ts=4 et ai

# ------------------------------------------------------------------------------
# Install and activate docker
# ------------------------------------------------------------------------------

set -e

dnf install docker -y
systemctl enable docker
systemctl start docker

# Allow ec2-user to issue docker commands.
usermod -a -G docker ec2-user
