# AI智能自动化测试平台

一个基于AI的智能自动化测试平台，支持需求分析、测试用例生成、接口测试、UI自动化测试和性能测试。

[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/)
[![Node](https://img.shields.io/badge/node-16+-green.svg)](https://nodejs.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.104+-green.svg)](https://fastapi.tiangolo.com/)
[![React](https://img.shields.io/badge/React-18.2+-blue.svg)](https://reactjs.org/)

## ✨ 功能特性

### 🤖 AI驱动功能
- **需求分析**: 基于自然语言需求自动分析测试要点、边界条件和风险点
- **智能测试用例生成**: 基于需求自动生成功能测试用例（正向、异常、边界）
- **API测试脚本生成**: 基于API文档自动生成接口测试脚本（支持OpenAPI/Swagger/Postman）
- **UI自动化脚本生成**: 智能识别DOM元素，自动生成UI测试脚本（支持Selenium/Playwright）
- **性能测试脚本生成**: 基于需求自动生成k6性能测试脚本
- **AI性能分析**: 自动分析性能测试结果，生成优化建议

### 🧪 测试管理
- **项目管理**: 项目创建、状态管理、配置管理
- **需求管理**: 需求跟踪、AI分析、测试关联
- **测试用例管理**: 测试用例CRUD、批量导入、AI生成
- **测试套件管理**: 测试套件创建、用例分组
- **测试运行管理**: 测试执行、状态监控、结果查看
- **性能测试管理**: k6脚本生成、执行、结果分析

### 🚀 测试执行
- **多类型测试支持**: 功能测试、API测试、UI自动化测试
- **异步执行**: 后台异步执行，不阻塞API
- **并行执行**: 支持测试用例并行执行
- **执行控制**: 支持启动、取消、暂停测试运行
- **实时监控**: 测试执行实时状态监控和进度显示

### 📊 测试报告
- **多种报告格式**: HTML、JSON、CSV、Markdown
- **详细测试结果**: 通过、失败、跳过、错误统计
- **性能指标分析**: 响应时间、吞吐量、错误率等
- **AI分析报告**: 自动生成测试分析和优化建议
- **报告下载**: 支持报告导出和下载

### 🎯 智能特性
- **智能元素识别**: 类似Testim的智能DOM元素定位
- **页面自动分析**: 自动爬取页面结构，理解页面元素
- **API文档解析**: 自动解析OpenAPI/Swagger/Postman文档
- **跨浏览器测试**: 支持Chrome、Firefox、Safari等
- **数据驱动测试**: 支持测试数据管理和参数化测试

### 🔧 技术特性
- **前后端分离**: React + TypeScript + FastAPI架构
- **AI模型支持**: OpenAI GPT-4、Deepseek、本地Ollama模型
- **数据库**: PostgreSQL + Redis
- **容器化部署**: Docker + Docker Compose
- **实时通信**: WebSocket支持（可选）

## 项目结构

```
ai_test_agent/
├── backend/                 # 后端服务
│   ├── app/
│   │   ├── api/            # API路由
│   │   ├── core/           # 核心配置
│   │   ├── models/         # 数据模型
│   │   ├── services/       # 业务逻辑
│   │   └── utils/          # 工具函数
│   ├── tests/              # 后端测试
│   └── requirements.txt    # Python依赖
├── frontend/               # 前端应用
│   ├── src/
│   │   ├── components/     # React组件
│   │   ├── pages/          # 页面组件
│   │   ├── services/       # API服务
│   │   └── utils/          # 工具函数
│   └── package.json        # Node.js依赖
├── ai_engine/              # AI引擎
│   ├── models/             # AI模型配置
│   ├── prompts/            # 提示词模板
│   └── processors/         # 处理器
└── docker-compose.yml      # Docker配置
```

## 🚀 快速开始

### 环境要求
- **Python**: 3.9+
- **Node.js**: 16+
- **Docker & Docker Compose**: 最新版本
- **PostgreSQL**: 15+ (或使用Docker)
- **Redis**: 7+ (或使用Docker)
- **k6**: 最新版本（性能测试需要，[安装指南](K6_SETUP.md)）

### 方式一：Docker Compose（推荐）

1. **克隆项目**
```bash
git clone https://github.com/github653224/intelligent-test-platform.git
cd ai_test_agent
```

2. **配置环境变量**
```bash
# 复制环境变量模板
cp .env.example .env

# 编辑 .env 文件，设置你的配置
# 至少需要设置：
# - OPENAI_API_KEY 或 DEEPSEEK_API_KEY（如果使用AI服务）
# - POSTGRES_PASSWORD（数据库密码）
# - SECRET_KEY（安全密钥）
```

3. **启动所有服务**
```bash
# 使用启动脚本
./start.sh

# 或使用 Docker Compose
docker-compose up -d
```

4. **访问应用**
- 🌐 **前端应用**: http://localhost:3000
- 🔧 **后端API**: http://localhost:8000
- 📚 **API文档**: http://localhost:8000/docs
- 🤖 **AI引擎**: http://localhost:8001

### 方式二：本地开发

1. **克隆项目**
```bash
git clone https://github.com/github653224/intelligent-test-platform.git
cd ai_test_agent
```

2. **配置环境变量**
```bash
cp .env.example .env
# 编辑 .env 文件
```

3. **启动数据库和Redis**
```bash
docker-compose up -d postgres redis
```

4. **初始化数据库**
```bash
cd backend
python init_db.py
```

5. **安装后端依赖**
```bash
cd backend
pip install -r requirements.txt
```

6. **启动后端服务**
```bash
PYTHONPATH=backend uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

7. **安装AI引擎依赖**
```bash
cd ai_engine
pip install -r requirements.txt
```

8. **启动AI引擎服务**
```bash
python -m ai_engine.main
```

9. **安装前端依赖**
```bash
cd frontend
npm install
```

10. **启动前端服务**
```bash
npm start
```

### 验证安装

```bash
# 检查后端API
curl http://localhost:8000/api/v1/health

# 检查AI引擎
curl http://localhost:8001/health

# 检查前端（浏览器访问）
open http://localhost:3000
```

## 📖 使用指南

### 1. 项目管理
1. 进入"项目管理"页面
2. 创建新项目，填写项目名称和描述
3. 设置项目状态和配置

### 2. 需求分析
1. 进入"需求管理"页面
2. 创建需求，输入自然语言需求描述
3. 点击"AI分析"，系统自动分析：
   - 测试要点和边界条件
   - 风险点评估
   - 测试策略建议

### 3. 测试用例生成
1. 进入"AI引擎" → "测试用例生成"
2. 输入需求描述和项目背景
3. 选择测试类型（功能测试/API测试/UI测试）
4. 点击"生成测试用例"
5. 选择需要的测试用例，保存到项目

### 4. API测试生成
1. 进入"AI引擎" → "API测试生成"
2. **方式一**：上传API文档（OpenAPI/Swagger/Postman）
   - 点击"上传API文档"
   - 系统自动解析并填充基础URL
3. **方式二**：手动输入API文档和基础URL
4. 选择测试场景（正常流程/异常处理/边界条件/性能测试）
5. 点击"生成API测试"
6. 查看生成的测试代码，可复制或下载

### 5. UI测试生成
1. 进入"AI引擎" → "UI测试生成"
2. 输入页面URL
3. 点击"分析页面"（可选，自动分析页面结构）
4. 输入业务需求/测试场景（例如："测试用户注册完整流程"）
5. 选择测试场景类型（正常流程/异常处理/边界条件等）
6. 点击"生成UI测试"
7. 查看生成的测试代码，可复制或下载

### 6. 性能测试
1. 进入"性能测试"页面
2. 创建性能测试，输入测试需求（例如："100并发用户持续30秒"）
3. 系统自动生成k6脚本
4. 点击"执行"开始测试
5. 测试完成后，点击"分析"查看AI分析报告

### 7. 测试执行
1. 进入"测试运行"页面
2. 创建测试运行，选择测试用例或测试套件
3. 配置执行参数（环境、超时时间等）
4. 点击"执行"开始测试
5. 实时查看执行进度和结果
6. 查看详细报告（HTML/JSON/CSV）

### 8. 测试报告
1. 在"测试运行"页面查看测试结果
2. 点击"查看详情"查看详细报告
3. 支持多种报告格式：
   - **摘要报告**：关键指标概览
   - **详细报告**：完整的测试结果
   - **HTML报告**：可视化报告
   - **JSON报告**：结构化数据
   - **CSV报告**：可导入Excel分析

## ⚙️ 配置说明

### 环境变量配置

复制 `.env.example` 为 `.env` 并配置以下变量：

```bash
# 数据库配置
POSTGRES_SERVER=localhost
POSTGRES_USER=postgres
POSTGRES_PASSWORD=your_password
POSTGRES_DB=ai_test_platform

# Redis配置
REDIS_URL=redis://localhost:6379/0

# AI模型配置（至少配置一个）
OPENAI_API_KEY=your_openai_api_key        # OpenAI API密钥
DEEPSEEK_API_KEY=your_deepseek_api_key    # Deepseek API密钥
OLLAMA_BASE_URL=http://localhost:11434     # Ollama本地模型地址
DEFAULT_AI_MODEL=ollama                    # 默认使用的AI模型

# 安全配置
SECRET_KEY=your_secret_key_here            # 请修改为随机字符串
ACCESS_TOKEN_EXPIRE_MINUTES=11520

# CORS配置
BACKEND_CORS_ORIGINS=http://localhost:3000,http://127.0.0.1:3000
```

### AI模型配置

支持三种AI模型：

1. **OpenAI API**（推荐用于生产环境）
   - 设置 `OPENAI_API_KEY`
   - 支持 GPT-4, GPT-3.5-turbo 等模型
   - 质量高，但需要付费

2. **Deepseek API**（性价比高）
   - 设置 `DEEPSEEK_API_KEY`
   - 支持 deepseek-chat 模型
   - 价格便宜，质量较好

3. **本地Ollama**（免费，推荐用于开发）
   - 设置 `OLLAMA_BASE_URL`
   - 支持 Llama3.2, CodeLlama 等本地模型
   - 完全免费，但需要本地资源

### 数据库初始化

首次运行需要初始化数据库：

```bash
cd backend
python init_db.py
```

或使用 Alembic 迁移：

```bash
cd backend
alembic upgrade head
```

### k6 安装（性能测试需要）

参考 [K6_SETUP.md](K6_SETUP.md) 安装 k6。

## 📁 项目结构

```
ai_test_agent/
├── backend/                 # 后端API服务
│   ├── app/
│   │   ├── api/v1/         # API路由
│   │   │   └── endpoints/  # 各个功能端点
│   │   ├── core/           # 核心配置
│   │   ├── models/         # 数据模型
│   │   ├── schemas/        # Pydantic模式
│   │   ├── services/        # 业务逻辑服务
│   │   └── utils/          # 工具函数
│   ├── alembic/            # 数据库迁移
│   ├── requirements.txt    # Python依赖
│   └── Dockerfile          # Docker配置
├── ai_engine/              # AI引擎服务
│   ├── models/             # AI模型客户端
│   ├── processors/         # 处理器（需求分析、测试生成等）
│   ├── main.py            # FastAPI主服务
│   ├── requirements.txt    # Python依赖
│   └── Dockerfile          # Docker配置
├── frontend/               # React前端
│   ├── src/
│   │   ├── components/     # React组件
│   │   ├── pages/          # 页面组件
│   │   ├── services/       # API服务
│   │   └── utils/         # 工具函数
│   ├── package.json        # Node.js依赖
│   └── Dockerfile          # Docker配置
├── .env.example            # 环境变量模板
├── .gitignore             # Git忽略文件
├── docker-compose.yml      # Docker编排配置
├── LICENSE                 # MIT许可证
├── CONTRIBUTING.md         # 贡献指南
└── README.md              # 项目说明
```

## 🔌 API文档

启动后端服务后，访问以下地址查看API文档：

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

## 🧪 测试

### 运行测试

```bash
# 后端测试
cd backend
pytest

# 前端测试
cd frontend
npm test

# AI引擎测试
python test_ai_engine.py
```

## 🐛 故障排除

### 常见问题

1. **数据库连接失败**
   - 检查 PostgreSQL 是否运行
   - 检查 `.env` 中的数据库配置
   - 检查数据库是否已初始化

2. **AI引擎无法连接**
   - 检查 AI引擎服务是否运行
   - 检查 API密钥是否正确
   - 检查网络连接

3. **前端无法访问后端**
   - 检查后端服务是否运行
   - 检查 CORS 配置
   - 检查端口是否被占用

4. **性能测试执行失败**
   - 检查 k6 是否已安装
   - 检查 k6 脚本语法
   - 查看后端日志

更多问题请查看 [QUICK_START.md](QUICK_START.md) 或提交 Issue。

## 🤝 贡献指南

我们欢迎所有形式的贡献！请查看 [CONTRIBUTING.md](CONTRIBUTING.md) 了解详细信息。

### 贡献流程

1. Fork 项目
2. 创建功能分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 创建 Pull Request

## 📄 许可证

本项目采用 MIT 许可证 - 查看 [LICENSE](LICENSE) 文件了解详情。

## 🙏 致谢

- [FastAPI](https://fastapi.tiangolo.com/) - 现代化的 Python Web 框架
- [React](https://reactjs.org/) - 用于构建用户界面的 JavaScript 库
- [Ant Design](https://ant.design/) - 企业级 UI 设计语言
- [k6](https://k6.io/) - 现代化的性能测试工具
- [OpenAI](https://openai.com/) - AI 模型服务
- [Ollama](https://ollama.ai/) - 本地 AI 模型运行环境

## 📞 支持

- 📧 提交 Issue: [GitHub Issues](https://github.com/github653224/intelligent-test-platform/issues)
- 📖 查看文档: [项目文档](https://github.com/github653224/intelligent-test-platform/wiki)
- 💬 讨论: [GitHub Discussions](https://github.com/github653224/intelligent-test-platform/discussions)

---

⭐ 如果这个项目对你有帮助，请给个 Star！ 