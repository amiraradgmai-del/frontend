#!/bin/sh
set -eu

interval="${BACKUP_INTERVAL_SECONDS:-86400}"
retention="${BACKUP_RETENTION_DAYS:-14}"

case "$interval" in *[!0-9]*|'') echo "Invalid backup interval" >&2; exit 1;; esac
case "$retention" in *[!0-9]*|'') echo "Invalid backup retention" >&2; exit 1;; esac

mkdir -p /backups
while true; do
  timestamp="$(date -u +%Y%m%dT%H%M%SZ)"
  target="/backups/tax_ai_${timestamp}.dump"
  temporary="${target}.tmp"
  pg_dump --format=custom --compress=9 --file="$temporary"
  pg_restore --list "$temporary" >/dev/null
  mv "$temporary" "$target"
  find /backups -type f -name 'tax_ai_*.dump' -mtime "+$retention" -delete
  echo "Backup completed: $target"
  sleep "$interval"
done
