# 🚀 AI智能自动化测试平台 - 快速启动指南

## 📋 项目概述

这是一个基于AI的智能自动化测试平台，具备以下核心功能：

- 🤖 **需求分析**: 基于自然语言需求自动分析测试要点
- 📝 **测试用例生成**: 自动生成功能测试、API测试、UI测试用例
- 🔧 **API测试**: 自动生成接口测试脚本
- 🎨 **UI自动化**: 智能识别DOM元素，生成UI测试脚本
- 🧠 **AI驱动**: 支持OpenAI API和本地Ollama模型

## 🛠️ 环境要求

- Docker & Docker Compose
- Python 3.9+
- Node.js 16+
- 4GB+ 内存

## ⚡ 快速启动

### 1. 克隆项目
```bash
git clone <repository-url>
cd ai_test_agent
```

### 2. 配置环境变量
```bash
# 编辑 .env 文件，设置你的OpenAI API密钥
cp .env.example .env
# 编辑 .env 文件，添加你的OpenAI API密钥
```

### 3. 启动服务
```bash
# 使用启动脚本（推荐）
./start.sh

# 或者手动启动
docker-compose up -d
```

### 4. 访问应用
- 🌐 **前端应用**: http://localhost:3000
- 🔧 **后端API**: http://localhost:8000
- 🤖 **AI引擎**: http://localhost:8001
- 📚 **API文档**: http://localhost:8000/docs

## 🧪 功能测试

### 测试AI引擎功能
```bash
python test_ai_engine.py
```

### 手动测试示例

#### 1. 需求分析
```bash
curl -X POST http://localhost:8001/analyze_requirement \
  -H "Content-Type: application/json" \
  -d '{
    "requirement_text": "用户登录功能：用户可以通过用户名和密码登录系统",
    "project_context": "电商网站用户认证模块",
    "test_focus": ["functional", "security"]
  }'
```

#### 2. 生成测试用例
```bash
curl -X POST http://localhost:8001/generate_test_cases \
  -H "Content-Type: application/json" \
  -d '{
    "requirement_text": "用户注册功能：用户填写邮箱、密码进行注册",
    "test_type": "functional",
    "test_scope": {"priority": "high"}
  }'
```

#### 3. 生成API测试
```bash
curl -X POST http://localhost:8001/generate_api_tests \
  -H "Content-Type: application/json" \
  -d '{
    "api_documentation": "POST /api/users/login",
    "base_url": "https://api.example.com",
    "test_scenarios": ["normal", "error"]
  }'
```

#### 4. 生成UI测试
```bash
curl -X POST http://localhost:8001/generate_ui_tests \
  -H "Content-Type: application/json" \
  -d '{
    "page_url": "https://example.com/login",
    "user_actions": ["输入用户名", "输入密码", "点击登录"],
    "test_scenarios": ["正常登录", "错误密码"]
  }'
```

## 🏗️ 项目架构

```
ai_test_agent/
├── backend/                 # 后端API服务
│   ├── app/
│   │   ├── api/            # API路由
│   │   ├── core/           # 核心配置
│   │   ├── models/         # 数据模型
│   │   └── services/       # 业务逻辑
│   └── requirements.txt    # Python依赖
├── ai_engine/              # AI引擎服务
│   ├── models/             # AI模型配置
│   ├── processors/         # 处理器
│   └── main.py            # 主服务
├── frontend/               # React前端
│   ├── src/
│   │   ├── components/     # React组件
│   │   ├── pages/          # 页面组件
│   │   └── services/       # API服务
│   └── package.json        # Node.js依赖
└── docker-compose.yml      # Docker配置
```

## 🔧 配置说明

### AI模型配置
支持两种AI模型：

1. **OpenAI API** (推荐)
   - 设置 `OPENAI_API_KEY` 环境变量
   - 支持 GPT-4, GPT-3.5-turbo 等模型

2. **本地Ollama**
   - 自动启动Ollama服务
   - 支持 Llama2, CodeLlama 等本地模型

### 数据库配置
- **PostgreSQL**: 存储项目、需求、测试用例等数据
- **Redis**: 缓存和会话管理

## 🚀 开发模式

### 本地开发
```bash
# 后端开发
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload

# AI引擎开发
cd ai_engine
pip install -r requirements.txt
python main.py

# 前端开发
cd frontend
npm install
npm start
```

### 生产部署
```bash
# 构建生产镜像
docker-compose -f docker-compose.prod.yml up -d

# 或者使用Kubernetes
kubectl apply -f k8s/
```

## 📊 监控和日志

### 查看服务状态
```bash
docker-compose ps
```

### 查看日志
```bash
# 查看所有服务日志
docker-compose logs

# 查看特定服务日志
docker-compose logs backend
docker-compose logs ai_engine
docker-compose logs frontend
```

### 健康检查
```bash
# 检查AI引擎
curl http://localhost:8001/health

# 检查后端API
curl http://localhost:8000/health
```

## 🐛 故障排除

### 常见问题

1. **AI引擎无法连接**
   ```bash
   # 检查Ollama服务
   docker-compose logs ollama
   
   # 重启AI引擎
   docker-compose restart ai_engine
   ```

2. **前端无法访问后端**
   ```bash
   # 检查后端服务
   docker-compose logs backend
   
   # 检查网络连接
   docker network ls
   ```

3. **数据库连接失败**
   ```bash
   # 检查PostgreSQL
   docker-compose logs postgres
   
   # 重启数据库
   docker-compose restart postgres
   ```

### 重置环境
```bash
# 停止所有服务
docker-compose down

# 清理数据
docker-compose down -v

# 重新启动
docker-compose up -d
```

## 📚 使用指南

### 1. 需求分析
1. 打开前端应用 http://localhost:3000
2. 进入"AI引擎"页面
3. 选择"需求分析"标签
4. 输入需求描述和项目背景
5. 点击"开始分析"

### 2. 生成测试用例
1. 在AI引擎页面选择"测试用例生成"
2. 输入需求描述
3. 选择测试类型（功能测试/API测试/UI测试）
4. 点击"生成测试用例"

### 3. 生成API测试
1. 选择"API测试生成"标签
2. 输入API文档和基础URL
3. 选择测试场景
4. 点击"生成API测试"

### 4. 生成UI测试
1. 选择"UI测试生成"标签
2. 输入页面URL和用户操作
3. 选择测试场景
4. 点击"生成UI测试"

## 🤝 贡献指南

1. Fork 项目
2. 创建功能分支
3. 提交更改
4. 推送到分支
5. 创建 Pull Request

## 📄 许可证

MIT License

## 📞 支持

如有问题，请提交 Issue 或联系开发团队。 