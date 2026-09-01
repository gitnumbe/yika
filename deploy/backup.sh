#!/usr/bin/env bash
# yika 数据库备份脚本（开发文档 §11.6）
# 用法（宿主 cron 每日 02:00）：
#   0 2 * * * bash /path/to/deploy/backup.sh postgres yika yika_pass >> /var/log/yika-backup.log 2>&1
set -euo pipefail

HOST="${1:-postgres}"
USER="${2:-yika}"
PASS="${3:-yika_pass}"
DB="${4:-yika}"
KEEP_DAYS="${KEEP_DAYS:-30}"
BACKUP_DIR="${BACKUP_DIR:-/backups/yika}"

TS=$(date +%Y%m%d_%H%M%S)
mkdir -p "$BACKUP_DIR"

echo "[$(date +%F_%T)] 开始备份 $DB"

# pg_dump（自定义格式，可 pg_restore）
docker exec "$HOST" pg_dump -U "$USER" -d "$DB" -Fc > "$BACKUP_DIR/yika_$TS.dump"

# 清理 30 天前
find "$BACKUP_DIR" -name "yika_*.dump" -mtime +"$KEEP_DAYS" -delete

# 备份完整性校验
SQL_FILES=$(find "$BACKUP_DIR" -name "yika_*.dump" | wc -l)
echo "[$(date +%F_%T)] 完成：$(ls -lh "$BACKUP_DIR/yika_$TS.dump" | awk '{print $5}')，累计 $SQL_FILES 份，保留 ${KEEP_DAYS} 天"
