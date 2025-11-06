# 数据持久化指南

## 问题：启动后数据被清空

如果启动后发现之前创建的项目、需求、测试用例都被清空了，可能的原因和解决方案如下：

## 可能的原因

### 1. Docker 容器被删除
如果使用了 `docker-compose down -v` 或删除了容器，数据会丢失。

### 2. Docker Volume 被删除
PostgreSQL 数据存储在 Docker volume 中，如果 volume 被删除，数据会丢失。

### 3. 数据库连接配置改变
如果数据库连接配置（服务器、数据库名）改变了，可能连接到不同的数据库实例。

## 解决方案

### 方案 1：检查 Docker Volume（推荐）

1. **检查 volume 是否存在**：
   ```bash
   docker volume ls | grep postgres
   ```

2. **检查 PostgreSQL 容器状态**：
   ```bash
   docker ps -a | grep postgres
   ```

3. **如果容器不存在，重新创建但不删除 volume**：
   ```bash
   # 只启动服务，不删除 volume
   docker-compose up -d postgres
   
   # 等待数据库启动（约 10 秒）
   sleep 10
   
   # 运行数据库迁移（如果需要）
   cd backend
   alembic upgrade head
   ```

### 方案 2：检查数据库连接

1. **验证数据库连接配置**：
   ```bash
   cd backend
   python check_db.py
   ```

2. **检查数据库中的数据**：
   如果使用 Docker：
   ```bash
   docker exec -it ai_test_postgres psql -U postgres -d ai_test_platform -c "SELECT COUNT(*) FROM projects;"
   ```

   如果使用本地 PostgreSQL：
   ```bash
   psql -U postgres -d ai_test_platform -c "SELECT COUNT(*) FROM projects;"
   ```

### 方案 3：数据备份和恢复

#### 备份数据

```bash
# 使用 Docker 备份
docker exec ai_test_postgres pg_dump -U postgres ai_test_platform > backup_$(date +%Y%m%d_%H%M%S).sql

# 或使用本地 PostgreSQL
pg_dump -U postgres ai_test_platform > backup_$(date +%Y%m%d_%H%M%S).sql
```

#### 恢复数据

```bash
# 使用 Docker 恢复
docker exec -i ai_test_postgres psql -U postgres ai_test_platform < backup_YYYYMMDD_HHMMSS.sql

# 或使用本地 PostgreSQL
psql -U postgres ai_test_platform < backup_YYYYMMDD_HHMMSS.sql
```

### 方案 4：保护 Docker Volume

**重要：** 使用以下命令时，**不要**使用 `-v` 参数，这会删除 volume：

```bash
# ✅ 正确：停止服务但不删除 volume
docker-compose down

# ❌ 错误：这会删除 volume，导致数据丢失
docker-compose down -v
```

## 预防措施

### 1. 定期备份

创建一个备份脚本 `backup_db.sh`：

```bash
#!/bin/bash
BACKUP_DIR="./backups"
mkdir -p $BACKUP_DIR
BACKUP_FILE="$BACKUP_DIR/backup_$(date +%Y%m%d_%H%M%S).sql"

docker exec ai_test_postgres pg_dump -U postgres ai_test_platform > $BACKUP_FILE
echo "✅ 备份完成: $BACKUP_FILE"
```

### 2. 使用命名 Volume（推荐）

在 `docker-compose.yml` 中，volume 已经配置为命名 volume：

```yaml
volumes:
  postgres_data:  # 这是命名 volume，数据会持久化
```

### 3. 检查数据持久化

运行以下命令检查数据是否持久化：

```bash
# 停止容器
docker-compose down

# 重新启动
docker-compose up -d postgres

# 等待启动
sleep 10

# 检查数据
docker exec ai_test_postgres psql -U postgres -d ai_test_platform -c "SELECT COUNT(*) FROM projects;"
```

如果数据还在，说明持久化正常。

## 常见问题

### Q: 如何查看 volume 中的数据？
A: 使用以下命令：
```bash
docker volume inspect ai_test_agent_postgres_data
```

### Q: 如何迁移数据到新环境？
A: 
1. 备份数据（见上面的备份命令）
2. 在新环境中恢复数据（见上面的恢复命令）

### Q: 如何清理数据但保留表结构？
A: 
```bash
docker exec ai_test_postgres psql -U postgres -d ai_test_platform -c "TRUNCATE projects, requirements, test_cases, test_steps, test_suites, test_runs CASCADE;"
```

### Q: 如何完全重置数据库？
A: **谨慎操作**，这会删除所有数据：
```bash
# 1. 停止服务
docker-compose down

# 2. 删除 volume（这会删除所有数据）
docker volume rm ai_test_agent_postgres_data

# 3. 重新启动
docker-compose up -d postgres

# 4. 等待启动后运行迁移
cd backend
alembic upgrade head
```

## 检查清单

在重启服务前，请确认：

- [ ] Docker volume 存在且未被删除
- [ ] 数据库连接配置正确
- [ ] 没有运行 `docker-compose down -v`
- [ ] 没有手动删除 volume
- [ ] 数据库容器正常启动

## 需要帮助？

如果数据仍然丢失，请提供以下信息：

1. Docker 容器状态：`docker ps -a`
2. Volume 列表：`docker volume ls`
3. 数据库连接配置：`backend/app/core/config.py`
4. 最近执行的命令历史

