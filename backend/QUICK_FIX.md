# 快速修复数据库连接问题

## 问题
`fe_sendauth: no password supplied` - 数据库连接缺少密码

## 已修复
1. ✅ 更新了 `app/core/config.py`，将默认密码设置为 "password"
2. ✅ 修复了 `.env` 文件路径读取问题
3. ✅ 确保密码在连接字符串中正确传递

## 现在请执行：

```bash
cd backend
alembic upgrade head
```

如果还有问题，可以手动设置环境变量：

```bash
cd backend
export POSTGRES_PASSWORD=password
alembic upgrade head
```

或者使用 Python 脚本直接创建表（绕过 Alembic）：

```bash
cd backend
python init_db.py
```

