#!/bin/bash
BACKUP_DIR="/opt/callcoach-crm/backups"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="$BACKUP_DIR/callcoach_db_$TIMESTAMP.sql.gz"
sudo -u postgres pg_dump callcoach_db | gzip > "$BACKUP_FILE"
find "$BACKUP_DIR" -name "callcoach_db_*.sql.gz" -mtime +7 -delete
echo "$(date): Backup done - $BACKUP_FILE ($(du -h "$BACKUP_FILE" | cut -f1))"
