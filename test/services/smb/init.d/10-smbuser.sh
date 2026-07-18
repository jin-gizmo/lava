#!/bin/bash

[ "$SMB_USER" = "" ] && echo SMB_USER must be set >&2 && exit 1
[ "$SMB_PASSWORD" = "" ] && echo SMB_PASSWORD must be set >&2 && exit 1

set -e

# Add the user to O/S
useradd --create-home "$SMB_USER"
echo "$SMB_USER:$SMB_PASSWORD" | chgpasswd

# Add them to SAMBA
smbpasswd -as "$SMB_USER" <<!
$SMB_PASSWORD
$SMB_PASSWORD
!

mkdir -p "/smb-data/$SMB_USER"
chown "$SMB_USER" "/smb-data/$SMB_USER"
chgrp "$SMB_USER" "/smb-data/$SMB_USER"

echo "Hello world" >  "/smb-data/$SMB_USER/hello.txt"
chown "$SMB_USER" "/smb-data/$SMB_USER/hello.txt"
chgrp "$SMB_USER" "/smb-data/$SMB_USER/hello.txt"
ls -laR "/smb-data"

