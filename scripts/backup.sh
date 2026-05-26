#!/bin/bash
# 数据备份脚本：打包 ChromaDB 向量库到带时间戳的压缩文件
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
BACKUP_DIR="$PROJECT_DIR/data/backups"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="$BACKUP_DIR/chroma_db_$TIMESTAMP.tar.gz"

mkdir -p "$BACKUP_DIR"

echo "正在备份向量库..."
tar -czf "$BACKUP_FILE" -C "$PROJECT_DIR/data" chroma_db
echo "备份完成：$BACKUP_FILE"

# 保留最近 7 份备份，自动清理旧的
ls -t "$BACKUP_DIR"/chroma_db_*.tar.gz | tail -n +8 | xargs -r rm -f
echo "已清理旧备份，当前保留 $(ls "$BACKUP_DIR"/chroma_db_*.tar.gz | wc -l) 份"
