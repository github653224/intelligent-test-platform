# 数据库设置指南

## 问题：执行 `alembic upgrade head` 报错

错误信息：`connection to server at "localhost" (127.0.0.1), port 5432 failed: Connection refused`

这意味着 PostgreSQL 数据库服务未运行。

## 解决方案

### 方案 1：使用 Docker Compose（推荐）

1. **启动 Docker Desktop**

2. **启动 PostgreSQL 数据库**：
   ```bash
   cd /Users/rock/Documents/ai_test_agent
   docker-compose up -d postgres
   ```

3. **等待数据库启动**（约 5-10 秒）

4. **运行 Alembic 迁移**：
   ```bash
   cd backend
   alembic upgrade head
   ```

### 方案 2：使用本地 PostgreSQL

如果你已经安装了 PostgreSQL：

1. **启动 PostgreSQL 服务**：
   ```bash
   # macOS (使用 Homebrew)
   brew services start postgresql@15
   
   # 或使用 pg_ctl
   pg_ctl -D /usr/local/var/postgres start
   ```

2. **创建数据库**：
   ```bash
   createdb ai_test_platform
   ```

3. **配置数据库连接**（如果需要）：
   编辑 `backend/app/core/config.py` 或创建 `.env` 文件：
   ```
   POSTGRES_SERVER=localhost
   POSTGRES_USER=postgres
   POSTGRES_PASSWORD=your_password
   POSTGRES_DB=ai_test_platform
   ```

4. **运行迁移**：
   ```bash
   cd backend
   alembic upgrade head
   ```

### 方案 3：直接使用 Python 脚本创建表（快速方案）

如果 Alembic 无法运行，可以使用提供的初始化脚本：

```bash
cd backend
python init_db.py
```

这个脚本会直接使用 SQLAlchemy 创建所有表，无需 Alembic。

## 验证数据库连接

运行以下命令测试数据库连接：

```bash
cd backend
python -c "from app.db.session import engine; engine.connect(); print('✅ 数据库连接成功！')"
```

## 数据库表结构

迁移文件会创建以下表：

- `projects` - 项目表
- `requirements` - 需求表
- `test_cases` - 测试用例表
- `test_steps` - 测试步骤表
- `test_suites` - 测试套件表
- `test_runs` - 测试运行表

## 常见问题

### Q: Docker 无法启动
A: 确保 Docker Desktop 已安装并运行。检查：`docker ps`

### Q: 端口 5432 已被占用
A: 检查是否有其他 PostgreSQL 实例在运行：
```bash
lsof -i :5432
```

### Q: 数据库连接密码错误
A: 检查 `backend/app/core/config.py` 中的数据库配置，或使用环境变量。

### Q: 表已存在错误
A: 如果需要重新创建表，先删除：
```bash
# 使用 Alembic
alembic downgrade base

# 或手动删除表（谨慎操作）
psql -U postgres -d ai_test_platform -c "DROP SCHEMA public CASCADE; CREATE SCHEMA public;"
```

## 下一步

数据库设置完成后，可以：

1. 启动后端服务：
   ```bash
   cd backend
   uvicorn app.main:app --reload --port 8000
   ```

2. 访问 API 文档：
   http://localhost:8000/docs

3. 测试 API 接口：
   - GET /api/v1/projects/
   - GET /api/v1/requirements/
   - GET /api/v1/test-cases/

