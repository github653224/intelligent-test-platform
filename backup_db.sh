#!/bin/bash
BACKUP_DIR="./backups"
mkdir -p $BACKUP_DIR
BACKUP_FILE="$BACKUP_DIR/backup_$(date +%Y%m%d_%H%M%S).sql"

# 检查是否使用 Docker
if docker ps | grep -q ai_test_postgres; then
    echo "📦 从 Docker 容器备份数据库..."
    docker exec ai_test_postgres pg_dump -U postgres ai_test_platform > $BACKUP_FILE
    echo "✅ 备份完成: $BACKUP_FILE"
elif command -v pg_dump &> /dev/null; then
    echo "📦 从本地 PostgreSQL 备份数据库..."
    pg_dump -U postgres ai_test_platform > $BACKUP_FILE
    echo "✅ 备份完成: $BACKUP_FILE"
else
    echo "❌ 无法找到 PostgreSQL 数据库"
    exit 1
fi
