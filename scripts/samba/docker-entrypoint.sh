#!/bin/sh
set -eu
mkdir -p /home/hqadmin/kcw-files
PASS_FILE="${SMB_PASS_FILE:-/run/smb.pass}"
if [ ! -s "$PASS_FILE" ]; then
  echo "missing Samba password file $PASS_FILE" >&2
  exit 1
fi
PASS=$(tr -d '\n\r' <"$PASS_FILE")
printf '%s\n%s\n' "$PASS" "$PASS" | smbpasswd -a hqadmin -s
smbpasswd -e hqadmin
exec /usr/sbin/smbd --foreground --no-process-group -s /etc/samba/smb.conf
