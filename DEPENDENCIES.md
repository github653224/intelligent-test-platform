# 依赖说明

本文档详细说明了项目的所有依赖及其用途。

## 后端依赖 (backend/requirements.txt)

### Web框架
- **fastapi==0.104.1**: 现代化的Python Web框架，用于构建API
- **uvicorn[standard]==0.24.0**: ASGI服务器，用于运行FastAPI应用
- **python-multipart==0.0.6**: 处理文件上传和表单数据

### 数据库
- **sqlalchemy==2.0.23**: ORM框架，用于数据库操作
- **alembic>=1.7.7**: 数据库迁移工具
- **psycopg2-binary>=2.9.5**: PostgreSQL数据库驱动

### 缓存
- **redis==5.0.1**: Redis客户端，用于缓存和会话管理

### 异步任务（可选）
- **celery==5.3.4**: 分布式任务队列（当前未使用，但已包含）
- **apscheduler==3.10.4**: 定时任务调度器，用于测试计划

### 数据验证
- **pydantic==2.5.0**: 数据验证库，FastAPI使用
- **pydantic-settings==2.1.0**: Pydantic设置管理

### 认证和安全
- **python-jose[cryptography]==3.3.0**: JWT令牌处理
- **passlib[bcrypt]==1.7.4**: 密码哈希（当前未使用，但已包含）

### HTTP客户端
- **httpx==0.25.2**: 异步HTTP客户端
- **aiohttp==3.9.1**: 异步HTTP客户端（用于测试执行）
- **requests==2.31.0**: 同步HTTP客户端

### AI模型
- **openai>=1.0.0**: OpenAI API客户端

### 文档解析
- **python-docx==1.1.0**: Word文档解析
- **PyPDF2==3.0.1**: PDF文档解析
- **pdfplumber==0.10.3**: PDF文档解析（更强大）
- **openpyxl==3.1.2**: Excel文档解析（.xlsx）
- **xlrd==2.0.1**: Excel文档解析（.xls）
- **xmindparser==1.0.10**: XMind思维导图解析
- **python-magic==0.4.27**: 文件类型检测
- **PyYAML==6.0.1**: YAML文件解析（API文档）

### 浏览器自动化
- **selenium==4.15.2**: 浏览器自动化框架
- **playwright==1.40.0**: 现代浏览器自动化框架（用于页面分析）

### 测试框架
- **pytest==7.4.3**: Python测试框架
- **pytest-asyncio==0.21.1**: 异步测试支持
- **pytest-cov==4.1.0**: 测试覆盖率

### 代码格式化
- **black==23.11.0**: 代码格式化工具
- **isort==5.12.0**: 导入排序工具
- **flake8==6.1.0**: 代码检查工具
- **mypy==1.7.1**: 类型检查工具

## AI引擎依赖 (ai_engine/requirements.txt)

### Web框架
- **fastapi==0.104.1**: FastAPI框架
- **uvicorn[standard]==0.24.0**: ASGI服务器
- **python-multipart==0.0.6**: 文件上传支持

### HTTP客户端
- **httpx==0.25.2**: 异步HTTP客户端（用于调用AI API）

### AI模型
- **openai==1.3.7**: OpenAI API客户端

### 数据验证
- **pydantic==2.5.0**: 数据验证

## 前端依赖 (frontend/package.json)

### 核心框架
- **react@^18.2.0**: React框架
- **react-dom@^18.2.0**: React DOM渲染
- **typescript@^4.9.5**: TypeScript支持

### UI组件库
- **antd@^5.12.8**: Ant Design组件库
- **@ant-design/icons@^5.2.6**: Ant Design图标

### 路由
- **react-router-dom@^6.20.1**: React路由

### HTTP客户端
- **axios@^1.6.2**: HTTP请求库

### 工具库
- **html2canvas@^1.4.1**: HTML转图片（用于报告导出）
- **jspdf@^3.0.3**: PDF生成（用于报告导出）
- **react-markdown@^10.1.0**: Markdown渲染
- **remark-gfm@^4.0.1**: GitHub风格Markdown
- **react-syntax-highlighter@^16.1.0**: 代码高亮
- **xlsx@^0.18.5**: Excel文件处理
- **markmap-lib@^0.18.12**: 思维导图库
- **markmap-view@^0.18.12**: 思维导图视图

### 开发工具
- **react-scripts@5.0.1**: Create React App脚本
- **@testing-library/react@^13.4.0**: React测试库
- **@testing-library/jest-dom@^5.17.0**: Jest DOM扩展
- **@testing-library/user-event@^13.5.0**: 用户事件模拟

## 系统依赖

### 数据库
- **PostgreSQL 15+**: 主数据库
- **Redis 7+**: 缓存和会话存储

### 性能测试
- **k6**: 性能测试工具（需要单独安装）
  - 安装指南: [K6_SETUP.md](K6_SETUP.md)

### 浏览器（UI测试需要）
- **Chrome/Chromium**: Selenium和Playwright需要
- **Firefox**: 可选
- **Safari**: 可选

## 版本说明

### Python版本
- 最低要求: Python 3.9
- 推荐版本: Python 3.10 或 3.11

### Node.js版本
- 最低要求: Node.js 16
- 推荐版本: Node.js 18 或 20

## 依赖更新

### 更新后端依赖
```bash
cd backend
pip install --upgrade -r requirements.txt
```

### 更新AI引擎依赖
```bash
cd ai_engine
pip install --upgrade -r requirements.txt
```

### 更新前端依赖
```bash
cd frontend
npm update
```

## 安全建议

1. **定期更新依赖**: 使用 `pip list --outdated` 和 `npm outdated` 检查过时依赖
2. **安全审计**: 使用 `pip-audit` 和 `npm audit` 检查安全漏洞
3. **锁定版本**: 生产环境建议锁定所有依赖版本
4. **最小权限**: 使用最小权限原则，只安装必要的依赖

## 可选依赖

以下依赖是可选的，根据需求安装：

- **celery**: 如果需要分布式任务队列
- **passlib**: 如果需要用户认证功能
- **pytest相关**: 仅开发环境需要
- **代码格式化工具**: 仅开发环境需要

