# AI智能自动化测试平台

一个基于AI的智能自动化测试平台，支持需求分析、测试用例生成、接口测试和UI自动化测试。

## 功能特性

### 🤖 AI驱动功能
- **需求分析**: 基于自然语言需求自动分析测试要点
- **智能测试用例生成**: 基于需求自动生成功能测试用例
- **接口测试脚本生成**: 自动生成API测试脚本
- **UI自动化脚本生成**: 智能识别DOM元素，生成UI测试脚本

### 🧪 测试能力
- **多类型测试支持**: 功能测试、接口测试、UI自动化测试
- **智能元素识别**: 类似Testim的智能DOM元素定位
- **跨浏览器测试**: 支持Chrome、Firefox、Safari等
- **并行执行**: 支持测试用例并行执行

### 🔧 技术特性
- **前后端分离**: React + FastAPI架构
- **AI模型支持**: OpenAI API + 本地Ollama
- **实时监控**: 测试执行实时状态监控
- **报告生成**: 详细的测试报告和分析

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

## 快速开始

### 环境要求
- Python 3.9+
- Node.js 16+
- Docker & Docker Compose
- PostgreSQL
- Redis

### 安装步骤

1. **克隆项目**
```bash
git clone <repository-url>
cd ai_test_agent
```

2. **启动后端服务**
```bash
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload
```

3. **启动前端服务**
```bash
cd frontend
npm install
npm start
```

4. **启动AI服务**
```bash
cd ai_engine
python main.py
```

## 使用指南

### 1. 需求分析
- 输入自然语言需求描述
- AI自动分析测试要点和边界条件
- 生成测试策略建议

### 2. 测试用例生成
- 基于需求自动生成功能测试用例
- 支持多种测试类型（正向、异常、边界）
- 自动生成测试数据

### 3. 接口测试
- 自动分析API文档
- 生成接口测试脚本
- 支持参数化测试

### 4. UI自动化测试
- 智能识别页面元素
- 自动生成UI测试脚本
- 支持录制回放功能

## 配置说明

### AI模型配置
支持多种AI模型：
- OpenAI GPT-4
- 本地Ollama模型
- 自定义模型

### 测试环境配置
- 支持多环境配置
- 测试数据管理
- 环境变量管理

## 贡献指南

欢迎提交Issue和Pull Request！

## 许可证

MIT License 